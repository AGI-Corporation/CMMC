"""
Assessment Router - SPRS score calculation and compliance dashboard.
These endpoints become MCP tools: calculate_sprs_score, get_compliance_dashboard.
"""

import os
import uuid
from datetime import UTC, datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (AgentRunRecord, AssessmentRecord,
                                 BlockchainTransaction, ControlRecord, get_db,
                                 get_latest_assessments)
from backend.services import blockchain_service, notification_service

router = APIRouter()


# SPRS point deductions per control (from DoD assessment methodology)
# Total possible score = 110 points
SPRS_DEDUCTIONS = {
    # High value controls (5 points each)
    "AC.2.006": 5,
    "AC.2.007": 5,
    "AC.3.017": 5,
    "AC.3.018": 5,
    "IA.3.083": 5,
    "IA.3.084": 5,
    "SC.3.177": 5,
    # Medium value controls (3 points each)
    "AC.1.001": 3,
    "AC.1.002": 3,
    "IA.1.076": 3,
    "IA.1.077": 3,
    "SC.1.175": 3,
    "SC.1.176": 3,
    "SI.1.210": 3,
    "SI.1.211": 3,
    "SI.1.212": 3,
    "SI.1.213": 3,
}


class DashboardSummary(BaseModel):
    total_controls: int
    implemented: int
    not_implemented: int
    partially_implemented: int
    not_started: int
    not_applicable: int
    compliance_percentage: float
    sprs_score: int
    by_domain: Dict[str, dict]
    by_level: Dict[str, dict]
    readiness: str


class SPRSResult(BaseModel):
    organization: str
    system_name: str
    sprs_score: int
    max_score: int
    controls_assessed: int
    controls_implemented: int
    controls_not_implemented: int
    deductions: List[dict]
    certification_level: str
    assessment_date: str


@router.get(
    "/dashboard",
    response_model=DashboardSummary,
    summary="Get Compliance Dashboard",
    description="Get overall CMMC compliance posture summary including implementation percentages, SPRS score, and breakdown by domain and level.",
)
async def get_compliance_dashboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ControlRecord))
    controls = result.scalars().all()

    assessments_map = await get_latest_assessments(db)

    by_domain = {}
    by_level = {
        "Level 1": {"total": 0, "implemented": 0},
        "Level 2": {"total": 0, "implemented": 0},
        "Level 3": {"total": 0, "implemented": 0},
    }
    implemented = not_implemented = partial = not_started = not_applicable = 0
    sprs_score = 110  # Start at max, deduct for non-implemented

    for c in controls:
        domain = c.domain
        level = c.level
        cid = c.id

        assessment = assessments_map.get(cid)
        status = assessment.status if assessment else "not_started"

        if domain not in by_domain:
            by_domain[domain] = {"total": 0, "implemented": 0, "not_implemented": 0}
        by_domain[domain]["total"] += 1
        if level in by_level:
            by_level[level]["total"] += 1

        if status == "implemented":
            implemented += 1
            by_domain[domain]["implemented"] += 1
            if level in by_level:
                by_level[level]["implemented"] += 1
        elif status == "not_implemented":
            not_implemented += 1
            by_domain[domain]["not_implemented"] += 1
            deduction = SPRS_DEDUCTIONS.get(cid, 1)
            sprs_score -= deduction
        elif status == "partially_implemented" or status == "partial":
            partial += 1
        elif status == "not_applicable":
            not_applicable += 1
        else:
            not_started += 1

    total = len(controls)
    pct = (implemented / total * 100) if total > 0 else 0

    if pct >= 100:
        readiness = "Ready for Certification"
    elif pct >= 80:
        readiness = "Near Compliant - Minor Gaps"
    elif pct >= 60:
        readiness = "In Progress - Significant Gaps"
    else:
        readiness = "Early Stage - Major Remediation Needed"

    return DashboardSummary(
        total_controls=total,
        implemented=implemented,
        not_implemented=not_implemented,
        partially_implemented=partial,
        not_started=not_started,
        not_applicable=not_applicable,
        compliance_percentage=round(pct, 2),
        sprs_score=max(sprs_score, -203),  # SPRS floor is -203
        by_domain=by_domain,
        by_level=by_level,
        readiness=readiness,
    )


@router.get(
    "/sprs",
    response_model=SPRSResult,
    summary="Calculate SPRS Score",
    description="Calculate the DoD Supplier Performance Risk System (SPRS) score based on current control implementation status. Score ranges from -203 to 110.",
)
async def calculate_sprs_score(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ControlRecord))
    controls = result.scalars().all()

    assessments_map = await get_latest_assessments(db)

    sprs = 110
    deductions_list = []
    implemented_count = not_implemented_count = 0

    for c in controls:
        cid = c.id
        assessment = assessments_map.get(cid)
        status = assessment.status if assessment else "not_started"

        if status == "implemented":
            implemented_count += 1
        elif status in [
            "not_implemented",
            "not_started",
            "partially_implemented",
            "partial",
        ]:
            not_implemented_count += 1
            deduction = SPRS_DEDUCTIONS.get(cid, 1)
            sprs -= deduction
            deductions_list.append({"control_id": cid, "deduction": deduction})

    if sprs >= 88:
        cert_level = "Level 2 Eligible"
    elif sprs >= 0:
        cert_level = "Level 1 Eligible"
    else:
        cert_level = "Below Threshold - Remediation Required"

    return SPRSResult(
        organization=os.getenv("SPRS_ORGANIZATION_NAME", "Organization"),
        system_name=os.getenv("SPRS_SYSTEM_NAME", "System"),
        sprs_score=max(sprs, -203),
        max_score=110,
        controls_assessed=len(controls),
        controls_implemented=implemented_count,
        controls_not_implemented=not_implemented_count,
        deductions=deductions_list,
        certification_level=cert_level,
        assessment_date=datetime.now(UTC).date().isoformat(),
    )


@router.post(
    "/promote/{run_id}", summary="Promote agent findings to official assessment records"
)
async def promote_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Convert an agent execution run into official assessment records."""
    query = select(AgentRunRecord).where(AgentRunRecord.id == run_id)
    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail=f"Agent run {run_id} not found")

    findings = run.findings
    promoted_count = 0

    # Logic for ICAM promotion
    if run.agent_type == "icam":
        results = findings.get("results", [])
        for res in results:
            new_ass = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=res["control_id"],
                status=res["status"],
                confidence=res["confidence"],
                notes=f"Promoted from {run.agent_type} agent run {run_id}. Findings: {', '.join(res['findings'])}",
                evidence_ids=[res["evidence_id"]],
                assessor=f"Agent: {run.agent_type}",
                assessment_date=datetime.now(UTC),
                poam_required=(
                    "true"
                    if res["status"]
                    in ["partial", "not_implemented", "partially_implemented"]
                    else "false"
                ),
            )
            db.add(new_ass)
            promoted_count += 1

    # Logic for DevSecOps promotion
    elif run.agent_type == "devsecops":
        # DSO provides overall confidence and detailed scan results
        # We'll map to specific controls it evaluated
        controls = run.controls_evaluated
        overall_conf = findings.get("overall_confidence", 0.0)
        status = findings.get("status", "partially_implemented")

        for cid in controls:
            new_ass = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=cid,
                status=status,
                confidence=overall_conf,
                notes=f"Promoted from {run.agent_type} agent run {run_id} for service {findings.get('service')}.",
                evidence_ids=[findings.get("image_scan", {}).get("evidence_id")],
                assessor=f"Agent: {run.agent_type}",
                assessment_date=datetime.now(UTC),
                poam_required=(
                    "true"
                    if status in ["partial", "not_implemented", "partially_implemented"]
                    else "false"
                ),
            )
            db.add(new_ass)
            promoted_count += 1

    # Logic for standard result agents (governance, awareness, icam)
    # These all use the unified {results: [...]} findings schema
    elif run.agent_type in ("governance", "awareness"):
        results = findings.get("results", [])
        for res in results:
            new_ass = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=res["control_id"],
                status=res["status"],
                confidence=res["confidence"],
                notes=(
                    f"Promoted from {run.agent_type} agent run {run_id}. "
                    f"Findings: {'; '.join(res.get('findings', []))}"
                ),
                evidence_ids=[res.get("evidence_id")] if res.get("evidence_id") else [],
                assessor=f"Agent: {run.agent_type}",
                assessment_date=datetime.now(UTC),
                poam_required=(
                    "true"
                    if res["status"]
                    in ["partial", "not_implemented", "partially_implemented"]
                    else "false"
                ),
            )
            db.add(new_ass)
            promoted_count += 1

    await db.commit()

    # Log promotion to blockchain
    try:
        tx = await blockchain_service.record_event(
            db,
            event_type="assessment_promoted",
            payload={
                "run_id": run_id,
                "agent_type": run.agent_type,
                "assessments_created": promoted_count,
            },
            actor=f"agent:{run.agent_type}",
        )
        await db.commit()
        notification_service.notify_assessment_promoted(
            run_id=run_id,
            agent_type=run.agent_type,
            assessments_created=promoted_count,
        )
        notification_service.notify_blockchain_recorded(
            transaction_id=tx["id"],
            sequence=tx["sequence"],
            event_type="assessment_promoted",
        )
    except Exception:
        pass  # blockchain failure must never break promotion

    return {
        "status": "promoted",
        "run_id": run_id,
        "assessments_created": promoted_count,
    }


# ---------------------------------------------------------------------------
# Assessment Submit endpoint
# ---------------------------------------------------------------------------


class AssessmentSubmit(BaseModel):
    control_id: str
    status: str  # implemented / partially_implemented / not_implemented / planned / na
    confidence: float = 0.0
    notes: Optional[str] = None
    assessor: Optional[str] = None
    evidence_ids: Optional[List[str]] = None
    poam_required: Optional[bool] = None


@router.post(
    "/submit",
    summary="Submit a manual assessment for a control",
    description="Submit an assessment for a CMMC control. Auto-logs to blockchain, auto-flags POA&M, and sends notification if required.",
)
async def submit_assessment(
    payload: AssessmentSubmit,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a manual assessment for a specific CMMC control.

    - Validates control existence.
    - Creates an AssessmentRecord.
    - Appends a signed blockchain transaction.
    - Auto-sets `poam_required=true` for non-implemented / partial statuses.
    - Emits a POAM notification when flagged.
    """
    # Validate control
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == payload.control_id)
    )
    ctrl = ctrl_result.scalar_one_or_none()
    if not ctrl:
        raise HTTPException(
            status_code=404,
            detail=f"Control '{payload.control_id}' not found in catalog.",
        )

    POAM_STATUSES = {"not_implemented", "partially_implemented", "partial", "planned"}
    poam_flag = (
        payload.poam_required
        if payload.poam_required is not None
        else (payload.status in POAM_STATUSES)
    )

    record = AssessmentRecord(
        id=str(uuid.uuid4()),
        control_id=payload.control_id,
        status=payload.status,
        confidence=max(0.0, min(1.0, payload.confidence)),
        notes=payload.notes,
        assessor=payload.assessor or "manual",
        assessment_date=datetime.now(UTC),
        evidence_ids=payload.evidence_ids or [],
        poam_required="true" if poam_flag else "false",
    )
    db.add(record)
    await db.flush()

    # Blockchain audit trail
    try:
        tx = await blockchain_service.record_event(
            db,
            event_type="assessment_submit",
            payload={
                "assessment_id": record.id,
                "control_id": record.control_id,
                "status": record.status,
                "confidence": record.confidence,
                "poam_required": poam_flag,
            },
            actor=record.assessor,
        )
        notification_service.notify_blockchain_recorded(
            transaction_id=tx["id"],
            sequence=tx["sequence"],
            event_type="assessment_submit",
        )
    except Exception:
        tx = None  # blockchain failure must never block assessment

    await db.commit()

    # POAM notification
    if poam_flag:
        notification_service.notify_poam_flagged(
            control_id=record.control_id,
            status=record.status,
            assessor=record.assessor,
            notes=record.notes or "",
        )

    return {
        "status": "submitted",
        "assessment_id": record.id,
        "control_id": record.control_id,
        "assessment_status": record.status,
        "poam_required": poam_flag,
        "blockchain_tx": tx["id"] if tx else None,
    }


# ---------------------------------------------------------------------------
# Assessment History
# ---------------------------------------------------------------------------


@router.get(
    "/history/{control_id}",
    summary="Get assessment history for a control",
    description="Return the full assessment history for a single CMMC control, newest first.",
)
async def get_assessment_history(
    control_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return all assessment records for a given control_id, newest first."""
    result = await db.execute(
        select(AssessmentRecord)
        .where(AssessmentRecord.control_id == control_id)
        .order_by(AssessmentRecord.assessment_date.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return {
        "control_id": control_id,
        "total": len(records),
        "history": [
            {
                "id": r.id,
                "status": r.status,
                "confidence": r.confidence,
                "assessor": r.assessor,
                "notes": r.notes,
                "evidence_ids": r.evidence_ids or [],
                "poam_required": r.poam_required,
                "assessment_date": r.assessment_date.isoformat(),
            }
            for r in records
        ],
    }


# ---------------------------------------------------------------------------
# Agent Run listing
# ---------------------------------------------------------------------------


@router.get(
    "/runs",
    summary="List agent assessment runs",
    description="List recent agent run records with optional filtering by agent type and status.",
)
async def list_agent_runs(
    agent_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all AgentRunRecords, newest first."""
    query = select(AgentRunRecord).order_by(AgentRunRecord.created_at.desc())
    if agent_type:
        query = query.where(AgentRunRecord.agent_type == agent_type)
    if status:
        query = query.where(AgentRunRecord.status == status)
    query = query.limit(limit)

    result = await db.execute(query)
    runs = result.scalars().all()
    return {
        "total": len(runs),
        "runs": [
            {
                "id": r.id,
                "agent_type": r.agent_type,
                "trigger": r.trigger,
                "scope": r.scope,
                "status": r.status,
                "controls_evaluated": r.controls_evaluated or [],
                "created_at": r.created_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
    }


# ---------------------------------------------------------------------------
# Domain-level summary with SPRS deduction breakdown
# ---------------------------------------------------------------------------


@router.get(
    "/summary",
    summary="Per-domain assessment summary with SPRS deductions",
    description="Return per-domain status counts, average confidence, SPRS deduction total, and compliance % — sorted by SPRS deduction descending (highest risk first).",
)
async def get_assessment_summary(db: AsyncSession = Depends(get_db)):
    """
    Aggregate assessment data by CMMC domain to surface the domains
    contributing most to SPRS score deduction.
    """
    ctrl_result = await db.execute(select(ControlRecord))
    controls = ctrl_result.scalars().all()
    assessments_map = await get_latest_assessments(db)

    domains: Dict[str, dict] = {}
    for c in controls:
        d = c.domain
        if d not in domains:
            domains[d] = {
                "domain": d,
                "total": 0,
                "implemented": 0,
                "partial": 0,
                "not_implemented": 0,
                "not_started": 0,
                "not_applicable": 0,
                "sprs_deduction": 0,
                "confidence_sum": 0.0,
                "assessed_count": 0,
            }
        domains[d]["total"] += 1
        ar = assessments_map.get(c.id)
        status = ar.status if ar else "not_started"
        if ar:
            domains[d]["assessed_count"] += 1
            domains[d]["confidence_sum"] += ar.confidence

        if status == "implemented":
            domains[d]["implemented"] += 1
        elif status in ("not_implemented", "not_started"):
            domains[d]["not_implemented"] += 1
            domains[d]["sprs_deduction"] += SPRS_DEDUCTIONS.get(c.id, 1)
        elif status in ("partially_implemented", "partial"):
            domains[d]["partial"] += 1
            # Partial gets half SPRS deduction
            domains[d]["sprs_deduction"] += SPRS_DEDUCTIONS.get(c.id, 1) * 0.5
        elif status == "not_applicable":
            domains[d]["not_applicable"] += 1
        else:
            domains[d]["not_started"] += 1

    # Compute averages and compliance %
    result_list = []
    for d, row in domains.items():
        avg_confidence = (
            round(row["confidence_sum"] / row["assessed_count"], 2)
            if row["assessed_count"] > 0 else 0.0
        )
        compliance_pct = (
            round(row["implemented"] / row["total"] * 100, 1)
            if row["total"] > 0 else 0.0
        )
        result_list.append({
            "domain": d,
            "total_controls": row["total"],
            "implemented": row["implemented"],
            "partial": row["partial"],
            "not_implemented": row["not_implemented"],
            "not_started": row["not_started"],
            "not_applicable": row["not_applicable"],
            "sprs_deduction": round(row["sprs_deduction"], 1),
            "avg_confidence": avg_confidence,
            "compliance_pct": compliance_pct,
        })

    # Sort by SPRS deduction descending (highest risk first)
    result_list.sort(key=lambda x: -x["sprs_deduction"])

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "domains": result_list,
        "total_domains": len(result_list),
    }


# ---------------------------------------------------------------------------
# In-process notification log endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/notifications",
    summary="Get in-process compliance event notifications",
    description="Return recent in-process notification events (POAM flags, agent runs, blockchain records). Supports filtering by event_type and severity.",
)
async def get_notifications(
    event_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
):
    """Return events from the in-memory notification log (last 500 events)."""
    events = notification_service.get_event_log(
        event_type=event_type,
        severity=severity,
        limit=limit,
    )
    return {
        "total": len(events),
        "events": events,
    }


# ---------------------------------------------------------------------------
# Blockchain chain integrity verification
# ---------------------------------------------------------------------------


@router.get(
    "/blockchain/verify",
    summary="Verify blockchain chain integrity",
    description="Walk every transaction in sequence order and verify payload hashes, HMAC signatures, and chain linkage.",
)
async def verify_blockchain(db: AsyncSession = Depends(get_db)):
    """Verify the tamper-evident blockchain ledger integrity."""
    return await blockchain_service.verify_chain(db)


@router.get(
    "/blockchain/ledger",
    summary="List blockchain transaction ledger",
    description="Return recent blockchain transactions (newest first).",
)
async def get_blockchain_ledger(
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return recent transactions from the blockchain ledger."""
    result = await db.execute(
        select(BlockchainTransaction)
        .order_by(BlockchainTransaction.sequence.desc())
        .limit(limit)
    )
    txns = result.scalars().all()
    return {
        "total": len(txns),
        "transactions": [
            {
                "id": tx.id,
                "sequence": tx.sequence,
                "event_type": tx.event_type,
                "payload_hash": tx.payload_hash,
                "previous_hash": tx.previous_hash,
                "actor": tx.actor,
                "created_at": tx.created_at.isoformat(),
            }
            for tx in txns
        ],
    }
