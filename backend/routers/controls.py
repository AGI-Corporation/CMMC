"""
CMMC Controls Router - FastAPI endpoints for control management.
These endpoints are automatically exposed as MCP tools via fastapi-mcp.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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
    """
    ⚡ BOLT OPTIMIZATION:
    - Replaced dual-query approach with single LEFT JOIN to reduce DB roundtrips.
    - Moved 'status' filtering to SQL level to reduce application memory and CPU usage.
    - Utilizes idx_control_date composite index for efficient latest-assessment lookup.
    """
    # Subquery for latest assessment date per control_id
    sub_q = (
        select(
            AssessmentRecord.control_id,
            func.max(AssessmentRecord.assessment_date).label("max_date")
        )
        .group_by(AssessmentRecord.control_id)
        .subquery()
    )

    # Join with AssessmentRecord to get the latest record
    latest_assessment_q = (
        select(AssessmentRecord)
        .join(
            sub_q,
            (AssessmentRecord.control_id == sub_q.c.control_id) &
            (AssessmentRecord.assessment_date == sub_q.c.max_date)
        )
        .subquery()
    )

    # Main query: Join ControlRecord with latest AssessmentRecord
    query = (
        select(ControlRecord, latest_assessment_q)
        .outerjoin(latest_assessment_q, ControlRecord.id == latest_assessment_q.c.control_id)
    )

    # Apply filters at database level
    if level:
        query = query.where(ControlRecord.level == level.value)
    if domain:
        query = query.where(ControlRecord.domain == domain.value)
    if status:
        if status == ImplementationStatus.NOT_STARTED:
            # Match if no assessment exists OR status is explicitly 'not_started'
            query = query.where(
                (latest_assessment_q.c.status == None) |
                (latest_assessment_q.c.status == status.value)
            )
        else:
            query = query.where(latest_assessment_q.c.status == status.value)

    result = await db.execute(query)
    rows = result.all()

    responses = []
    for row in rows:
        # row contains (ControlRecord, id, system_name, control_id, status, confidence, ...)
        # Row elements can be accessed by index or by column name if using Row objects correctly
        # In SQLAlchemy 2.0, result.all() returns Row objects.
        c = row[0]  # ControlRecord is the first element because of select(ControlRecord, ...)

        # Access assessment data from the subquery columns in the row
        impl_status = row.status if row.status else "not_started"

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
            evidence_count=len(row.evidence_ids) if row.evidence_ids and isinstance(row.evidence_ids, list) else 0,
            notes=row.notes if row.notes else None,
            confidence=row.confidence if row.confidence else 0.0,
            poam_required=(row.poam_required == "true") if row.poam_required else False
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
