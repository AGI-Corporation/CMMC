"""
Assessment Router - SPRS score calculation and compliance dashboard.
These endpoints become MCP tools: calculate_sprs_score, get_compliance_dashboard.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (AgentRunRecord, AssessmentRecord,
                                 ControlRecord, get_db, get_latest_assessments)
from backend.services import blockchain_service as bc
from backend.services import notification_service as notify

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

    # Agents that emit a standard {"results": [...]} findings structure
    STANDARD_RESULT_AGENTS = {
        "icam",
        "data_protection",
        "infrastructure",
        "governance",
        "operations",
        "remediation",
        "supply_chain",
        "awareness",
    }

    if run.agent_type in STANDARD_RESULT_AGENTS:
        # Standard format: findings["results"] is a list of assessment dicts,
        # each with control_id, status, confidence, findings[], evidence_id.
        results = findings.get("results", [])
        for res in results:
            ctrl_id = res.get("control_id")
            if not ctrl_id:
                continue
            finding_msgs = res.get("findings", [])
            notes_text = (
                f"Promoted from {run.agent_type} agent run {run_id}."
                + (f" Findings: {', '.join(finding_msgs)}" if finding_msgs else "")
            )
            evidence_id = res.get("evidence_id")
            new_ass = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=ctrl_id,
                status=res.get("status", "not_started"),
                confidence=res.get("confidence", 0.0),
                notes=notes_text,
                evidence_ids=[evidence_id] if evidence_id else [],
                assessor=f"Agent: {run.agent_type}",
                assessment_date=datetime.now(UTC),
                poam_required=(
                    "true"
                    if res.get("status") in [
                        "partial", "not_implemented", "partially_implemented"
                    ]
                    else "false"
                ),
            )
            db.add(new_ass)
            promoted_count += 1

    elif run.agent_type == "devsecops":
        # DevSecOps provides overall confidence at the run level rather than per-control
        controls = run.controls_evaluated or []
        overall_conf = findings.get("overall_confidence", 0.0)
        status = findings.get("status", "partially_implemented")
        service = findings.get("service", "")

        for cid in controls:
            new_ass = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=cid,
                status=status,
                confidence=overall_conf,
                notes=f"Promoted from {run.agent_type} agent run {run_id}"
                      + (f" for service {service}." if service else "."),
                evidence_ids=[findings.get("image_scan", {}).get("evidence_id")]
                if findings.get("image_scan", {}).get("evidence_id")
                else [],
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

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Promotion not supported for agent type '{run.agent_type}'.",
        )

    # Record the promotion event on the immutable audit chain
    await bc.record_event(
        db,
        event_type="assessment_promoted",
        actor=f"agent:{run.agent_type}",
        payload={
            "run_id": run_id,
            "agent_type": run.agent_type,
            "assessments_created": promoted_count,
            "promoted_at": datetime.now(UTC).isoformat(),
        },
    )

    await db.commit()
    return {
        "status": "promoted",
        "run_id": run_id,
        "agent_type": run.agent_type,
        "assessments_created": promoted_count,
    }


# ── Request/Response models for manual assessment submission ───────────────────

class AssessmentSubmission(BaseModel):
    control_id: str
    status: str  # implemented / partially_implemented / planned / not_implemented / na
    confidence: float = 0.0  # 0.0 – 1.0
    notes: Optional[str] = None
    evidence_ids: Optional[List[str]] = None
    assessor: Optional[str] = None
    system_name: Optional[str] = None
    poam_required: Optional[bool] = None


class AssessmentSubmissionResponse(BaseModel):
    submission_id: str
    control_id: str
    status: str
    confidence: float
    assessor: Optional[str]
    assessment_date: str
    poam_required: bool
    blockchain_tx_id: Optional[str] = None


@router.post(
    "/submit",
    response_model=AssessmentSubmissionResponse,
    summary="Submit a manual control assessment",
    description=(
        "Submit a human assessor's finding for a specific CMMC control. "
        "Creates an AssessmentRecord, auto-determines POAM requirement, "
        "and logs the event to the blockchain audit chain. "
        "Maps to CMMC CA.2.157, CA.2.158, and AU.2.041."
    ),
)
async def submit_assessment(
    submission: AssessmentSubmission,
    db: AsyncSession = Depends(get_db),
):
    """
    Directly submit a compliance assessment for a CMMC control.

    The `status` field must be one of:
      - implemented
      - partially_implemented
      - planned
      - not_implemented
      - na

    A POAM entry is automatically flagged when status is not_implemented or
    partially_implemented and confidence < 1.0.
    """
    valid_statuses = {
        "implemented", "partially_implemented", "planned",
        "not_implemented", "na", "partial", "not_started",
    }
    if submission.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{submission.status}'. Must be one of: {sorted(valid_statuses)}",
        )

    if not (0.0 <= submission.confidence <= 1.0):
        raise HTTPException(
            status_code=422,
            detail="confidence must be between 0.0 and 1.0.",
        )

    # Verify control exists
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == submission.control_id)
    )
    if ctrl_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail=f"Control '{submission.control_id}' not found in catalog.",
        )

    # Determine POAM requirement
    poam_needed = (
        submission.poam_required
        if submission.poam_required is not None
        else submission.status in {"not_implemented", "partially_implemented", "partial"}
    )

    submission_id = str(uuid.uuid4())
    record = AssessmentRecord(
        id=submission_id,
        system_name=submission.system_name or os.getenv("SPRS_SYSTEM_NAME", "System"),
        control_id=submission.control_id,
        status=submission.status,
        confidence=submission.confidence,
        notes=submission.notes,
        evidence_ids=submission.evidence_ids or [],
        assessor=submission.assessor or "manual",
        assessment_date=datetime.now(UTC),
        poam_required="true" if poam_needed else "false",
    )
    db.add(record)

    # Log to audit chain
    tx = await bc.record_event(
        db,
        event_type="assessment_submitted",
        actor=submission.assessor or "manual",
        payload={
            "submission_id": submission_id,
            "control_id": submission.control_id,
            "status": submission.status,
            "confidence": submission.confidence,
            "poam_required": poam_needed,
            "submitted_at": datetime.now(UTC).isoformat(),
        },
    )

    await db.commit()

    # Fire POAM notification if this assessment flagged a gap
    if poam_needed:
        notify.notify_poam_flagged(
            control_id=submission.control_id,
            status=submission.status,
            confidence=submission.confidence,
            assessor=submission.assessor or "manual",
            notes=submission.notes,
        )

    return AssessmentSubmissionResponse(
        submission_id=submission_id,
        control_id=submission.control_id,
        status=submission.status,
        confidence=submission.confidence,
        assessor=submission.assessor or "manual",
        assessment_date=record.assessment_date.isoformat(),
        poam_required=poam_needed,
        blockchain_tx_id=tx.id,
    )


@router.get(
    "/history/{control_id}",
    summary="Get assessment history for a control",
    description=(
        "Return all historical assessment records for a specific control ID in "
        "reverse chronological order. Useful for audit trails and trend analysis. "
        "Maps to AU.2.042 and CA.2.157."
    ),
)
async def get_assessment_history(
    control_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return the full assessment history for a CMMC control."""
    # Ensure control exists
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == control_id)
    )
    ctrl = ctrl_result.scalar_one_or_none()
    if ctrl is None:
        raise HTTPException(
            status_code=404,
            detail=f"Control '{control_id}' not found in catalog.",
        )

    query = (
        select(AssessmentRecord)
        .where(AssessmentRecord.control_id == control_id)
        .order_by(AssessmentRecord.assessment_date.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "control_id": control_id,
        "control_title": ctrl.title,
        "total_assessments": len(records),
        "history": [
            {
                "assessment_id": r.id,
                "status": r.status,
                "confidence": r.confidence,
                "assessor": r.assessor,
                "system_name": r.system_name,
                "notes": r.notes,
                "poam_required": r.poam_required == "true",
                "assessment_date": r.assessment_date.isoformat()
                if r.assessment_date
                else None,
                "evidence_ids": r.evidence_ids or [],
            }
            for r in records
        ],
    }


@router.get(
    "/runs",
    summary="List agent run records",
    description=(
        "Return a paginated list of agent run records, optionally filtered by "
        "agent type, status, or trigger. Supports pagination via limit/offset."
    ),
)
async def list_agent_runs(
    agent_type: Optional[str] = Query(None, description="Filter by agent type (e.g. icam, governance)"),
    status: Optional[str] = Query(None, description="Filter by status (running, completed, failed)"),
    trigger: Optional[str] = Query(None, description="Filter by trigger (manual, schedule, code_push, incident, assessment)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated agent run records with optional filters."""
    query = select(AgentRunRecord).order_by(AgentRunRecord.created_at.desc())

    if agent_type:
        query = query.where(AgentRunRecord.agent_type == agent_type)
    if status:
        query = query.where(AgentRunRecord.status == status)
    if trigger:
        query = query.where(AgentRunRecord.trigger == trigger)

    # Count total matching
    count_query = select(func.count(AgentRunRecord.id))
    if agent_type:
        count_query = count_query.where(AgentRunRecord.agent_type == agent_type)
    if status:
        count_query = count_query.where(AgentRunRecord.status == status)
    if trigger:
        count_query = count_query.where(AgentRunRecord.trigger == trigger)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    paged_query = query.limit(limit).offset(offset)
    result = await db.execute(paged_query)
    runs = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "runs": [
            {
                "run_id": r.id,
                "agent_type": r.agent_type,
                "trigger": r.trigger,
                "scope": r.scope,
                "status": r.status,
                "controls_evaluated": r.controls_evaluated or [],
                "mistral_model": r.mistral_model,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
    }



# ── POAM Management Models ─────────────────────────────────────────────────────

class POAMUpdateRequest(BaseModel):
    target_completion_date: Optional[datetime] = None
    notes: Optional[str] = None
    responsible_party: Optional[str] = None
    poam_status: Optional[str] = None  # open / in_progress / closed / cancelled


class POAMEntry(BaseModel):
    control_id: str
    control_title: Optional[str] = None
    domain: Optional[str] = None
    level: Optional[str] = None
    status: str
    confidence: float
    assessor: Optional[str] = None
    assessment_date: Optional[str] = None
    target_completion_date: Optional[str] = None
    notes: Optional[str] = None
    poam_status: str
    days_open: Optional[int] = None


@router.get(
    "/poam",
    summary="List all open POA&M entries",
    description=(
        "Return a paginated list of controls that have been flagged as requiring a "
        "Plan of Action & Milestones (POA&M). Entries are sourced from the latest "
        "assessment record for each control where poam_required='true'. "
        "Maps to CMMC CA.2.158 and RA.2.141."
    ),
)
async def list_poam_entries(
    domain: Optional[str] = Query(None, description="Filter by control domain (e.g. AC, IA)"),
    level: Optional[str] = Query(None, description="Filter by CMMC level (Level 1, Level 2, Level 3)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return all controls with an active POA&M requirement (latest assessment poam_required=true)."""
    # Fetch all controls, optionally filtered
    ctrl_query = select(ControlRecord)
    if domain:
        ctrl_query = ctrl_query.where(ControlRecord.domain == domain)
    if level:
        ctrl_query = ctrl_query.where(ControlRecord.level == level)
    ctrl_result = await db.execute(ctrl_query)
    controls = {c.id: c for c in ctrl_result.scalars().all()}

    if not controls:
        return {"total": 0, "limit": limit, "offset": offset, "entries": []}

    # Fetch latest assessments for these controls
    assessments_map = await get_latest_assessments(db, control_ids=list(controls.keys()))

    # Collect POA&M entries
    poam_entries = []
    now = datetime.now(UTC)
    for ctrl_id, ctrl in controls.items():
        assessment = assessments_map.get(ctrl_id)
        if assessment is None or assessment.poam_required != "true":
            continue

        days_open = None
        if assessment.assessment_date:
            ad = assessment.assessment_date
            # SQLite returns naive datetimes; normalize to UTC-aware for arithmetic
            if ad.tzinfo is None:
                ad = ad.replace(tzinfo=UTC)
            days_open = (now - ad).days

        # Derive poam_status from status field
        if assessment.status == "implemented":
            poam_status = "closed"
        elif assessment.status == "planned":
            poam_status = "in_progress"
        elif assessment.status == "not_implemented":
            poam_status = "open"
        else:
            poam_status = "open"

        poam_entries.append(
            POAMEntry(
                control_id=ctrl_id,
                control_title=ctrl.title,
                domain=ctrl.domain,
                level=ctrl.level,
                status=assessment.status,
                confidence=assessment.confidence,
                assessor=assessment.assessor,
                assessment_date=assessment.assessment_date.isoformat()
                if assessment.assessment_date
                else None,
                target_completion_date=assessment.next_review.isoformat()
                if assessment.next_review
                else None,
                notes=assessment.notes,
                poam_status=poam_status,
                days_open=days_open,
            )
        )

    total = len(poam_entries)
    paged = poam_entries[offset: offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [e.model_dump() for e in paged],
    }


@router.patch(
    "/poam/{control_id}",
    summary="Update a POA&M entry's target date and notes",
    description=(
        "Update the remediation target date, responsible party, notes, and/or "
        "POA&M status for the latest assessment of a specific control. "
        "Maps to CMMC CA.2.158 (plan of action and milestones). "
        "Creating a new assessment record preserves the full audit trail."
    ),
)
async def update_poam_entry(
    control_id: str,
    update: POAMUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update POA&M details for a control by appending a revised assessment record."""
    # Verify control exists
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == control_id)
    )
    ctrl = ctrl_result.scalar_one_or_none()
    if ctrl is None:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    # Get latest assessment
    ass_result = await db.execute(
        select(AssessmentRecord)
        .where(AssessmentRecord.control_id == control_id)
        .order_by(AssessmentRecord.assessment_date.desc())
        .limit(1)
    )
    current = ass_result.scalar_one_or_none()

    if current is None:
        raise HTTPException(
            status_code=404,
            detail=f"No assessment found for control {control_id}. Submit an assessment first.",
        )

    if current.poam_required != "true":
        raise HTTPException(
            status_code=400,
            detail=f"Control {control_id} does not have an active POA&M (poam_required=false).",
        )

    # Build update notes
    update_parts = []
    if update.notes:
        update_parts.append(update.notes)
    if update.responsible_party:
        update_parts.append(f"Responsible party: {update.responsible_party}.")
    if update.poam_status:
        update_parts.append(f"POA&M status updated to: {update.poam_status}.")
    merged_notes = " ".join(update_parts) if update_parts else current.notes

    # Derive implementation status from poam_status
    new_status = current.status
    if update.poam_status == "closed":
        new_status = "implemented"
    elif update.poam_status == "in_progress":
        new_status = "planned"

    new_assessment = AssessmentRecord(
        id=str(uuid.uuid4()),
        control_id=control_id,
        system_name=current.system_name,
        status=new_status,
        confidence=current.confidence,
        notes=merged_notes,
        evidence_ids=list(current.evidence_ids or []),
        assessor=update.responsible_party or current.assessor,
        assessment_date=datetime.now(UTC),
        next_review=update.target_completion_date or current.next_review,
        poam_required="true" if new_status not in ("implemented", "na") else "false",
    )
    db.add(new_assessment)
    await db.commit()

    return {
        "updated": True,
        "control_id": control_id,
        "control_title": ctrl.title,
        "new_assessment_id": new_assessment.id,
        "status": new_assessment.status,
        "poam_required": new_assessment.poam_required == "true",
        "target_completion_date": new_assessment.next_review.isoformat()
        if new_assessment.next_review
        else None,
        "notes": new_assessment.notes,
    }


@router.get(
    "/trend",
    summary="Compliance trend — assessment counts over time",
    description=(
        "Return aggregated assessment submission counts and status breakdowns "
        "grouped by day or week, over a configurable number of periods. "
        "Useful for compliance dashboard trend charts. "
        "Maps to AU.3.045 (correlate audit records) and CA.2.157 (monitor controls)."
    ),
)
async def get_compliance_trend(
    window: str = Query(
        "day",
        description="Aggregation window: 'day' or 'week'",
        pattern="^(day|week)$",
    ),
    periods: int = Query(30, ge=1, le=90, description="Number of periods to return"),
    db: AsyncSession = Depends(get_db),
):
    """Return assessment submission counts aggregated by time window.

    Note: SQLite stores datetime values as naive (timezone-unaware) strings.
    Bucket boundaries are stripped of timezone info before use in WHERE clauses
    to avoid mixed-aware/naive comparison errors.
    """
    from sqlalchemy import func as sqlfunc

    now = datetime.now(UTC)
    if window == "week":
        delta = timedelta(weeks=1)
    else:
        delta = timedelta(days=1)

    # Build time buckets
    buckets = []
    for i in range(periods - 1, -1, -1):
        bucket_end = now - i * delta
        bucket_start = bucket_end - delta
        buckets.append((bucket_start, bucket_end))

    result_rows = []
    for start, end in buckets:
        # SQLite stores datetimes as naive strings; strip timezone for comparison
        start_naive = start.replace(tzinfo=None)
        end_naive = end.replace(tzinfo=None)
        q = select(AssessmentRecord).where(
            AssessmentRecord.assessment_date >= start_naive,
            AssessmentRecord.assessment_date < end_naive,
        )
        r = await db.execute(q)
        records = r.scalars().all()

        status_counts: Dict[str, int] = {}
        for rec in records:
            status_counts[rec.status] = status_counts.get(rec.status, 0) + 1

        result_rows.append(
            {
                "period_start": start.date().isoformat(),
                "period_end": end.date().isoformat(),
                "total_submissions": len(records),
                "implemented": status_counts.get("implemented", 0),
                "partially_implemented": status_counts.get("partially_implemented", 0)
                + status_counts.get("partial", 0),
                "planned": status_counts.get("planned", 0),
                "not_implemented": status_counts.get("not_implemented", 0),
                "not_started": status_counts.get("not_started", 0),
            }
        )

    return {
        "window": window,
        "periods": periods,
        "data": result_rows,
    }


@router.get(
    "/summary",
    summary="Per-domain compliance summary with SPRS contribution",
    description=(
        "Return per-domain assessment status counts and the SPRS score contribution "
        "for each domain. Useful for identifying the highest-impact remediation targets. "
        "Maps to CA.2.157 (continuous monitoring) and RA.2.141 (risk assessment)."
    ),
)
async def get_assessment_summary(
    db: AsyncSession = Depends(get_db),
):
    """Aggregate assessment status counts and SPRS deductions by CMMC domain."""
    # Load all controls
    ctrl_result = await db.execute(select(ControlRecord))
    controls = ctrl_result.scalars().all()

    # Build control map and get latest assessments
    ctrl_map = {c.id: c for c in controls}
    assessments_map = await get_latest_assessments(db)

    # Aggregate by domain
    domain_data: Dict[str, Dict] = {}
    for ctrl in controls:
        d = ctrl.domain
        if d not in domain_data:
            domain_data[d] = {
                "domain": d,
                "total_controls": 0,
                "implemented": 0,
                "partially_implemented": 0,
                "planned": 0,
                "not_implemented": 0,
                "not_started": 0,
                "na": 0,
                "sprs_deduction": 0,
                "avg_confidence": [],
            }
        domain_data[d]["total_controls"] += 1

        assessment = assessments_map.get(ctrl.id)
        status = assessment.status if assessment else "not_started"
        confidence = assessment.confidence if assessment else 0.0

        # Normalise status key
        if status == "partial":
            status = "partially_implemented"

        if status in domain_data[d]:
            domain_data[d][status] += 1
        else:
            domain_data[d]["not_started"] += 1

        if status in ("not_implemented", "not_started"):
            domain_data[d]["sprs_deduction"] += ctrl.score_value or 1
        elif status == "partially_implemented":
            domain_data[d]["sprs_deduction"] += (ctrl.score_value or 1) // 2

        if assessment:
            domain_data[d]["avg_confidence"].append(confidence)

    # Finalise avg_confidence
    summary_rows = []
    for row in domain_data.values():
        confidences = row.pop("avg_confidence")
        row["avg_confidence"] = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
        row["compliance_pct"] = round(
            row["implemented"] / row["total_controls"] * 100, 1
        ) if row["total_controls"] else 0.0
        summary_rows.append(row)

    # Sort by sprs_deduction descending (highest impact first)
    summary_rows.sort(key=lambda r: r["sprs_deduction"], reverse=True)

    total_sprs = max(-203, 110 - sum(r["sprs_deduction"] for r in summary_rows))

    return {
        "sprs_score": total_sprs,
        "total_controls": len(controls),
        "domains": summary_rows,
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/notifications",
    summary="List recent compliance notification events",
    description=(
        "Return recent compliance notification events fired by the platform "
        "(POAM flags, agent findings, blockchain alerts). Events are stored in "
        "an in-process ring buffer (last 500 events). Filter by event_type and "
        "severity. Maps to IR.2.093 (track incidents) and AU.2.042 (review logs)."
    ),
)
async def list_notifications(
    event_type: Optional[str] = Query(
        None,
        description="Filter by event type: poam_flagged | agent_finding | blockchain_alert",
    ),
    severity: Optional[str] = Query(
        None, description="Filter by severity: critical | high | medium | low | info"
    ),
    limit: int = Query(50, ge=1, le=500),
):
    """Return recent compliance notification events from the in-process log."""
    events = notify.get_event_log(event_type=event_type, severity=severity, limit=limit)
    return {
        "total": len(events),
        "limit": limit,
        "events": events,
    }
