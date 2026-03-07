"""
CMMC Controls Router - FastAPI endpoints for control management.
These endpoints are automatically exposed as MCP tools via fastapi-mcp.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import aliased

from backend.db.database import get_db, ControlRecord, AssessmentRecord
from backend.models.control import (
    Control, ControlResponse, ControlListResponse,
    ControlUpdate, CMMCLevel, ControlDomain, ImplementationStatus
)

router = APIRouter()

@router.get(
    "/",
    response_model=ControlListResponse,
    summary="List CMMC Controls",
    description="List all CMMC controls, optionally filtered by level or domain. Returns controls with current implementation status."
)
async def list_controls(
    level: Optional[CMMCLevel] = Query(None, description="Filter by CMMC level (Level 1, Level 2, Level 3)"),
    domain: Optional[ControlDomain] = Query(None, description="Filter by control domain (AC, AU, CM, etc.)"),
    status: Optional[ImplementationStatus] = Query(None, description="Filter by implementation status"),
    db: AsyncSession = Depends(get_db)
):
    # ⚡ Bolt Optimization: Use a single JOINed query with DB-level filtering
    # This reduces DB roundtrips and memory usage by filtering at the SQL level.
    # The 'idx_control_date' composite index on AssessmentRecord (control_id, assessment_date)
    # makes the max_date subquery significantly faster.

    # Subquery to find the latest assessment date for each control
    sub_q = (
        select(
            AssessmentRecord.control_id,
            func.max(AssessmentRecord.assessment_date).label("max_date")
        )
        .group_by(AssessmentRecord.control_id)
        .subquery()
    )

    # Subquery to get the full latest assessment records
    latest_ass_q = (
        select(AssessmentRecord)
        .join(
            sub_q,
            (AssessmentRecord.control_id == sub_q.c.control_id) &
            (AssessmentRecord.assessment_date == sub_q.c.max_date)
        )
        .subquery()
    )

    latest_ass = aliased(AssessmentRecord, latest_ass_q)

    # Main query joining controls with their latest assessment
    query = select(ControlRecord, latest_ass).outerjoin(
        latest_ass, ControlRecord.id == latest_ass.control_id
    )

    # Apply filters at the database level
    if level:
        query = query.where(ControlRecord.level == level.value)
    if domain:
        query = query.where(ControlRecord.domain == domain.value)
    if status:
        if status == ImplementationStatus.NOT_STARTED:
            # Handle controls with either explicit 'not_started' or no assessment record
            query = query.where((latest_ass.status == None) | (latest_ass.status == "not_started"))
        else:
            query = query.where(latest_ass.status == status.value)

    result = await db.execute(query)

    responses = []
    for c, a in result:
        impl_status = a.status if a else "not_started"

        responses.append(ControlResponse(
            control=Control(
                id=c.id,
                title=c.title,
                description=c.description,
                domain=c.domain,
                level=c.level,
                nist_mapping=c.nist_mapping,
                weight=c.score_value
            ),
            implementation_status=impl_status,
            evidence_count=len(a.evidence_ids) if a and isinstance(a.evidence_ids, list) else 0,
            notes=a.notes if a else None,
            confidence=a.confidence if a else 0.0,
            poam_required=(a.poam_required == "true") if a else False
        ))

    return ControlListResponse(controls=responses, total=len(responses), level_filter=level, domain_filter=domain)


@router.get(
    "/{control_id}",
    response_model=ControlResponse,
    summary="Get Control Detail",
    description="Get full details of a specific CMMC control by its ID (e.g., AC.1.001)."
)
async def get_control_detail(control_id: str, db: AsyncSession = Depends(get_db)):
    query = select(ControlRecord).where(ControlRecord.id == control_id)
    result = await db.execute(query)
    c = result.scalar_one_or_none()

    if not c:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    a_query = select(AssessmentRecord).where(AssessmentRecord.control_id == control_id).order_by(AssessmentRecord.assessment_date.desc())
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
            weight=c.score_value
        ),
        implementation_status=assessment.status if assessment else "not_started",
        evidence_count=len(assessment.evidence_ids) if assessment and isinstance(assessment.evidence_ids, list) else 0,
        notes=assessment.notes if assessment else None,
        confidence=assessment.confidence if assessment else 0.0,
        poam_required=(assessment.poam_required == "true") if assessment else False
    )


@router.patch(
    "/{control_id}",
    response_model=ControlResponse,
    summary="Update Control Assessment Status",
    description="Update the implementation status, notes, and responsible party for a CMMC control."
)
async def update_control_status(control_id: str, update: ControlUpdate, db: AsyncSession = Depends(get_db)):
    query = select(ControlRecord).where(ControlRecord.id == control_id)
    result = await db.execute(query)
    c = result.scalar_one_or_none()

    if not c:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    import uuid
    from datetime import datetime, UTC

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
        poam_required="true" if update.poam_required else "false"
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
            weight=c.score_value
        ),
        implementation_status=update.implementation_status,
        notes=update.notes,
        confidence=new_assessment.confidence,
        poam_required=update.poam_required
    )


@router.get(
    "/domain/{domain}",
    response_model=ControlListResponse,
    summary="Get Controls by Domain",
    description="Get all CMMC controls for a specific domain (e.g., AC for Access Control)."
)
async def get_controls_by_domain(domain: ControlDomain, db: AsyncSession = Depends(get_db)):
    return await list_controls(domain=domain, db=db)
