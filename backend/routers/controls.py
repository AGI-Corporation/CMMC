"""
CMMC Controls Router - FastAPI endpoints for control management.
These endpoints are automatically exposed as MCP tools via fastapi-mcp.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AssessmentRecord, ControlRecord, get_db
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
    """
    Optimized list_controls using single query JOIN for performance.
    """
    # 1. Get latest assessment subquery
    sub_q = (
        select(
            AssessmentRecord.control_id,
            func.max(AssessmentRecord.assessment_date).label("max_date"),
        )
        .group_by(AssessmentRecord.control_id)
        .subquery()
    )

    # 2. Main query joining Controls with latest Assessments
    query = (
        select(ControlRecord, AssessmentRecord)
        .outerjoin(sub_q, ControlRecord.id == sub_q.c.control_id)
        .outerjoin(
            AssessmentRecord,
            (AssessmentRecord.control_id == sub_q.c.control_id)
            & (AssessmentRecord.assessment_date == sub_q.c.max_date),
        )
    )

    # 3. Apply Filters at DB level
    if level:
        query = query.where(ControlRecord.level == level.value)
    if domain:
        query = query.where(ControlRecord.domain == domain.value)
    if status:
        if status.value == "not_started":
            # "not_started" means no assessment record exists
            query = query.where(AssessmentRecord.id.is_(None))
        else:
            query = query.where(AssessmentRecord.status == status.value)

    result = await db.execute(query)
    rows = result.all()

    responses = [
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
            implementation_status=a.status if a else "not_started",
            evidence_count=(
                len(a.evidence_ids) if a and isinstance(a.evidence_ids, list) else 0
            ),
            notes=a.notes if a else None,
            confidence=a.confidence if a else 0.0,
            poam_required=(a.poam_required == "true") if a else False,
        )
        for c, a in rows
    ]

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
