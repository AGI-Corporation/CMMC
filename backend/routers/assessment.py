"""
Assessment Router - SPRS score calculation and compliance dashboard.
These endpoints become MCP tools: calculate_sprs_score, get_compliance_dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
import uuid
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.db.database import get_db, ControlRecord, AssessmentRecord, AgentRunRecord, get_latest_assessments

router = APIRouter()


# SPRS point deductions per control (from DoD assessment methodology)
# Total possible score = 110 points
SPRS_DEDUCTIONS = {
    # High value controls (5 points each)
    "AC.2.006": 5, "AC.2.007": 5, "AC.3.017": 5, "AC.3.018": 5,
    "IA.3.083": 5, "IA.3.084": 5, "SC.3.177": 5,
    # Medium value controls (3 points each)  
    "AC.1.001": 3, "AC.1.002": 3, "IA.1.076": 3, "IA.1.077": 3,
    "SC.1.175": 3, "SC.1.176": 3, "SI.1.210": 3, "SI.1.211": 3,
    "SI.1.212": 3, "SI.1.213": 3,
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
    description="Get overall CMMC compliance posture summary including implementation percentages, SPRS score, and breakdown by domain and level."
)
async def get_compliance_dashboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ControlRecord))
    controls = result.scalars().all()

    assessments_map = await get_latest_assessments(db)
    
    by_domain = {}
    by_level = {"Level 1": {"total": 0, "implemented": 0}, "Level 2": {"total": 0, "implemented": 0}, "Level 3": {"total": 0, "implemented": 0}}
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
            # Consistent with sprs endpoint: partially implemented also deducts points
            deduction = SPRS_DEDUCTIONS.get(cid, 1)
            sprs_score -= deduction
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
        readiness=readiness
    )


@router.get(
    "/sprs",
    response_model=SPRSResult,
    summary="Calculate SPRS Score",
    description="Calculate the DoD Supplier Performance Risk System (SPRS) score based on current control implementation status. Score ranges from -203 to 110."
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
        elif status in ["not_implemented", "not_started", "partially_implemented", "partial"]:
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
        assessment_date=datetime.now(UTC).date().isoformat()
    )

@router.post("/promote/{run_id}", summary="Promote agent findings to official assessment records")
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
                poam_required="true" if res["status"] in ["partial", "not_implemented", "partially_implemented"] else "false",
                fingerprint=run.fingerprint # Inherit fingerprint for provenance
            )
            db.add(new_ass)
            promoted_count += 1

    # Logic for DevSecOps promotion
    elif run.agent_type == "devsecops":
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
                poam_required="true" if status in ["partial", "not_implemented", "partially_implemented"] else "false",
                fingerprint=run.fingerprint
            )
            db.add(new_ass)
            promoted_count += 1

    # Logic for Infra agent promotion
    elif run.agent_type == "infra":
        agent_findings = findings.get("findings", [])
        for f in agent_findings:
            new_ass = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=f["control_id"],
                status=f["status"],
                confidence=f["confidence"],
                notes=f"Promoted from {run.agent_type} agent run {run_id}. Finding: {f['finding']}",
                evidence_ids=[findings.get("evidence_id")],
                assessor=f"Agent: {run.agent_type}",
                assessment_date=datetime.now(UTC),
                poam_required="true" if f["status"] in ["partial", "not_implemented", "partially_implemented"] else "false",
                fingerprint=run.fingerprint
            )
            db.add(new_ass)
            promoted_count += 1

    # Logic for Data agent promotion
    elif run.agent_type == "data":
        agent_findings = findings.get("findings", [])
        for f in agent_findings:
            new_ass = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=f["control_id"],
                status=f["status"],
                confidence=f["confidence"],
                notes=f"Promoted from {run.agent_type} agent run {run_id}. Finding: {f['finding']}",
                evidence_ids=[findings.get("evidence_id")],
                assessor=f"Agent: {run.agent_type}",
                assessment_date=datetime.now(UTC),
                poam_required="true" if f["status"] in ["partial", "not_implemented", "partially_implemented"] else "false",
                fingerprint=run.fingerprint
            )
            db.add(new_ass)
            promoted_count += 1

    await db.commit()
    return {"status": "promoted", "run_id": run_id, "assessments_created": promoted_count}
