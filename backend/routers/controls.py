"""
CMMC Controls Router - FastAPI endpoints for control management.
These endpoints are automatically exposed as MCP tools via fastapi-mcp.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (AssessmentRecord, ControlRecord, EvidenceRecord,
                                 get_db, get_latest_assessments)
from backend.models.control import (CMMCLevel, Control, ControlDomain,
                                    ControlListResponse, ControlResponse,
                                    ControlUpdate, ImplementationStatus)

router = APIRouter()


@router.get(
    "/",
    response_model=ControlListResponse,
    summary="List CMMC Controls",
    description="List all CMMC controls, optionally filtered by level or domain. Returns controls with current implementation status.",
)
async def list_controls(
    level: Optional[CMMCLevel] = Query(
        None, description="Filter by CMMC level (Level 1, Level 2, Level 3)"
    ),
    domain: Optional[ControlDomain] = Query(
        None, description="Filter by control domain (AC, AU, CM, etc.)"
    ),
    status: Optional[ImplementationStatus] = Query(
        None, description="Filter by implementation status"
    ),
    db: AsyncSession = Depends(get_db),
):
    # Base query for controls
    query = select(ControlRecord)
    if level:
        query = query.where(ControlRecord.level == level.value)
    if domain:
        query = query.where(ControlRecord.domain == domain.value)

    ctrl_result = await db.execute(query)
    controls_data = ctrl_result.scalars().all()

    # Extract IDs to fetch only required assessments
    control_ids = [c.id for c in controls_data]

    # Optimization: Use shared helper with ID filtering
    assessments_map = (
        await get_latest_assessments(db, control_ids=control_ids) if control_ids else {}
    )

    responses = []
    for c in controls_data:
        assessment = assessments_map.get(c.id)
        impl_status = assessment.status if assessment else "not_started"

        if status and impl_status != status.value:
            continue

        responses.append(
            ControlResponse(
                control=Control(
                    id=c.id,
                    title=c.title,
                    description=c.description,
                    domain=c.domain,
                    level=c.level,
                    nist_mapping=c.nist_mapping,
                    weight=c.score_value,
                ),
                implementation_status=impl_status,
                evidence_count=(
                    len(assessment.evidence_ids)
                    if assessment and isinstance(assessment.evidence_ids, list)
                    else 0
                ),
                notes=assessment.notes if assessment else None,
                confidence=assessment.confidence if assessment else 0.0,
                poam_required=(
                    (assessment.poam_required == "true") if assessment else False
                ),
            )
        )

    return ControlListResponse(
        controls=responses,
        total=len(responses),
        level_filter=level,
        domain_filter=domain,
    )


@router.get(
    "/{control_id}",
    response_model=ControlResponse,
    summary="Get Control Detail",
    description="Get full details of a specific CMMC control by its ID (e.g., AC.1.001).",
)
async def get_control_detail(control_id: str, db: AsyncSession = Depends(get_db)):
    query = select(ControlRecord).where(ControlRecord.id == control_id)
    result = await db.execute(query)
    c = result.scalar_one_or_none()

    if not c:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    a_query = (
        select(AssessmentRecord)
        .where(AssessmentRecord.control_id == control_id)
        .order_by(AssessmentRecord.assessment_date.desc())
    )
    a_result = await db.execute(a_query)
    assessment = a_result.scalars().first()

    return ControlResponse(
        control=Control(
            id=c.id,
            title=c.title,
            description=c.description,
            domain=c.domain,
            level=c.level,
            nist_mapping=c.nist_mapping,
            weight=c.score_value,
        ),
        implementation_status=assessment.status if assessment else "not_started",
        evidence_count=(
            len(assessment.evidence_ids)
            if assessment and isinstance(assessment.evidence_ids, list)
            else 0
        ),
        notes=assessment.notes if assessment else None,
        confidence=assessment.confidence if assessment else 0.0,
        poam_required=(assessment.poam_required == "true") if assessment else False,
    )


@router.patch(
    "/{control_id}",
    response_model=ControlResponse,
    summary="Update Control Assessment Status",
    description="Update the implementation status, notes, and responsible party for a CMMC control.",
)
async def update_control_status(
    control_id: str, update: ControlUpdate, db: AsyncSession = Depends(get_db)
):
    query = select(ControlRecord).where(ControlRecord.id == control_id)
    result = await db.execute(query)
    c = result.scalar_one_or_none()

    if not c:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    import uuid
    from datetime import UTC, datetime

    new_assessment = AssessmentRecord(
        id=str(uuid.uuid4()),
        control_id=control_id,
        status=update.implementation_status.value,
        notes=update.notes,
        assessor=update.responsible_party,
        next_review=update.target_completion_date,
        assessment_date=datetime.now(UTC),
        evidence_ids=update.evidence_ids or [],
        confidence=update.confidence or 0.0,
        poam_required="true" if update.poam_required else "false",
    )
    db.add(new_assessment)
    await db.commit()

    return ControlResponse(
        control=Control(
            id=c.id,
            title=c.title,
            description=c.description,
            domain=c.domain,
            level=c.level,
            nist_mapping=c.nist_mapping,
            weight=c.score_value,
        ),
        implementation_status=update.implementation_status,
        notes=update.notes,
        confidence=new_assessment.confidence,
        poam_required=update.poam_required,
    )


@router.get(
    "/domain/{domain}",
    response_model=ControlListResponse,
    summary="Get Controls by Domain",
    description="Get all CMMC controls for a specific domain (e.g., AC for Access Control).",
)
async def get_controls_by_domain(
    domain: ControlDomain, db: AsyncSession = Depends(get_db)
):
    return await list_controls(domain=domain, db=db)


@router.get(
    "/{control_id}/evidence",
    summary="List evidence linked to a control",
    description=(
        "Return all evidence artifact IDs and metadata linked to a specific CMMC "
        "control, sourced from the assessment history's evidence_ids lists. "
        "Maps to AU.2.041 and AU.2.042 (evidence traceability)."
    ),
)
async def list_control_evidence(
    control_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return all evidence records linked to a CMMC control via assessment records."""
    # Ensure control exists
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == control_id)
    )
    ctrl = ctrl_result.scalar_one_or_none()
    if ctrl is None:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    # Collect all evidence IDs referenced in assessments for this control
    ass_result = await db.execute(
        select(AssessmentRecord)
        .where(AssessmentRecord.control_id == control_id)
        .order_by(AssessmentRecord.assessment_date.desc())
    )
    assessments = ass_result.scalars().all()

    seen_ids: set = set()
    evidence_ids: list = []
    for a in assessments:
        for eid in (a.evidence_ids or []):
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                evidence_ids.append(eid)

    # Fetch the actual EvidenceRecord rows for the collected IDs
    evidence_rows = []
    if evidence_ids:
        ev_result = await db.execute(
            select(EvidenceRecord).where(EvidenceRecord.id.in_(evidence_ids))
        )
        evidence_rows = ev_result.scalars().all()

    return {
        "control_id": control_id,
        "control_title": ctrl.title,
        "evidence_count": len(evidence_rows),
        "evidence": [
            {
                "evidence_id": e.id,
                "title": e.title,
                "evidence_type": e.evidence_type,
                "source_system": e.source_system,
                "zt_pillar": e.zt_pillar,
                "description": e.description,
                "uri": e.uri,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evidence_rows
        ],
    }
