"""
Evidence Management Router
AGI Corporation 2026

Handles CMMC evidence artifact CRUD - REST and MCP tool.
Evidence types: log, scan, policy, diagram, screenshot, report, configuration.
All evidence records include ZT pillar, capability ID, and control mappings.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AssessmentRecord, ControlRecord, EvidenceRecord, get_db
from backend.models.evidence import (EvidenceCreate, EvidenceListResponse,
                                     EvidenceResponse)

router = APIRouter()


@router.post(
    "/",
    response_model=EvidenceResponse,
    summary="Upload evidence artifact for a CMMC control",
)
async def create_evidence(
    evidence: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Associate an evidence artifact with a CMMC control.
    Required fields: control_id, zt_pillar, evidence_type, title, source_system.
    """
    record = EvidenceRecord(
        id=str(uuid.uuid4()),
        control_id=evidence.control_id,
        zt_pillar=evidence.zt_pillar,
        zt_capability_id=evidence.zt_capability_id,
        evidence_type=evidence.evidence_type.value,
        title=evidence.title,
        description=evidence.description,
        source_system=evidence.source_system,
        uri=evidence.uri,
        reviewer=evidence.reviewer,
        review_cycle_days=evidence.review_cycle_days,
        metadata_=evidence.metadata or {},
        created_at=datetime.now(UTC),
    )
    db.add(record)
    await db.flush()
    return EvidenceResponse(
        id=record.id,
        control_id=record.control_id,
        zt_pillar=record.zt_pillar,
        zt_capability_id=record.zt_capability_id,
        evidence_type=record.evidence_type,
        title=record.title,
        description=record.description,
        source_system=record.source_system,
        uri=record.uri,
        reviewer=record.reviewer,
        review_cycle_days=record.review_cycle_days,
        metadata=record.metadata_ or {},
        created_at=record.created_at,
    )


@router.get(
    "/", response_model=EvidenceListResponse, summary="List all evidence artifacts"
)
async def list_evidence(
    control_id: Optional[str] = None,
    zt_pillar: Optional[str] = None,
    evidence_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List evidence with optional filters by control, pillar, or type."""
    query = select(EvidenceRecord)
    if control_id:
        query = query.where(EvidenceRecord.control_id == control_id)
    if zt_pillar:
        query = query.where(EvidenceRecord.zt_pillar == zt_pillar)
    if evidence_type:
        query = query.where(EvidenceRecord.evidence_type == evidence_type)
    result = await db.execute(query)
    records = result.scalars().all()
    items = [
        EvidenceResponse(
            id=r.id,
            control_id=r.control_id,
            zt_pillar=r.zt_pillar,
            zt_capability_id=r.zt_capability_id,
            evidence_type=r.evidence_type,
            title=r.title,
            description=r.description,
            source_system=r.source_system,
            uri=r.uri,
            reviewer=r.reviewer,
            review_cycle_days=r.review_cycle_days,
            metadata=r.metadata_ or {},
            created_at=r.created_at,
        )
        for r in records
    ]
    return EvidenceListResponse(total=len(items), evidence=items)


@router.get(
    "/review-due",
    response_model=EvidenceListResponse,
    summary="List evidence artifacts that have exceeded their review cycle",
)
async def list_review_due(
    days_overdue: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Return evidence artifacts whose review cycle has elapsed.

    An artifact is due for review when:
        created_at + review_cycle_days ≤ today + days_overdue

    Set days_overdue=0 (default) to find all currently overdue items.
    Set days_overdue=30 to also include items that will become overdue within 30 days.

    Maps to AU.2.042 (review and analysis of audit records) and
    CA.2.157 (periodic security assessment).
    """
    now = datetime.now(UTC)
    # We fetch all and filter in Python to keep the SQLite-compatible approach
    # (SQLite stores datetimes as strings; arithmetic is simpler in Python)
    result = await db.execute(select(EvidenceRecord))
    records = result.scalars().all()

    due_records = []
    for r in records:
        if r.review_cycle_days and r.review_cycle_days > 0 and r.created_at:
            # SQLite returns naive datetimes; compare in UTC-naive space
            created = r.created_at.replace(tzinfo=None)
            review_due_date = created + timedelta(days=r.review_cycle_days)
            threshold = now.replace(tzinfo=None) + timedelta(days=days_overdue)
            if review_due_date <= threshold:
                due_records.append(r)

    items = [
        EvidenceResponse(
            id=r.id,
            control_id=r.control_id,
            zt_pillar=r.zt_pillar,
            zt_capability_id=r.zt_capability_id,
            evidence_type=r.evidence_type,
            title=r.title,
            description=r.description,
            source_system=r.source_system,
            uri=r.uri,
            reviewer=r.reviewer,
            review_cycle_days=r.review_cycle_days,
            metadata=r.metadata_ or {},
            created_at=r.created_at,
        )
        for r in due_records
    ]
    return EvidenceListResponse(total=len(items), evidence=items)


@router.get(
    "/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Get a specific evidence artifact",
)
async def get_evidence(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single evidence record by ID."""
    result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")
    return EvidenceResponse(
        id=record.id,
        control_id=record.control_id,
        zt_pillar=record.zt_pillar,
        zt_capability_id=record.zt_capability_id,
        evidence_type=record.evidence_type,
        title=record.title,
        description=record.description,
        source_system=record.source_system,
        uri=record.uri,
        reviewer=record.reviewer,
        review_cycle_days=record.review_cycle_days,
        metadata=record.metadata_ or {},
        created_at=record.created_at,
    )


@router.delete("/{evidence_id}", summary="Delete an evidence artifact")
async def delete_evidence(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove an evidence record."""
    result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")
    await db.delete(record)
    return {"deleted": evidence_id}


@router.post(
    "/{evidence_id}/link-control/{control_id}",
    summary="Link an evidence artifact to an additional CMMC control",
    description=(
        "Attach an existing evidence artifact to a CMMC control by adding the "
        "evidence ID to the latest assessment record for that control. If no "
        "assessment record exists for the control, a new 'not_started' placeholder "
        "is created. The evidence record's primary control_id remains unchanged. "
        "Maps to AU.2.041 (evidence traceability)."
    ),
)
async def link_evidence_to_control(
    evidence_id: str,
    control_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Link an evidence artifact to a CMMC control's latest assessment."""
    # Verify evidence exists
    ev_result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
    )
    evidence = ev_result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")

    # Verify control exists
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == control_id)
    )
    if ctrl_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    # Find the latest assessment for this control
    ass_result = await db.execute(
        select(AssessmentRecord)
        .where(AssessmentRecord.control_id == control_id)
        .order_by(AssessmentRecord.assessment_date.desc())
        .limit(1)
    )
    assessment = ass_result.scalar_one_or_none()

    if assessment is None:
        # Create a placeholder assessment so we can attach the evidence
        assessment = AssessmentRecord(
            id=str(uuid.uuid4()),
            control_id=control_id,
            status="not_started",
            confidence=0.0,
            notes="Auto-created to link evidence artifact.",
            evidence_ids=[evidence_id],
            assessor="system",
            assessment_date=datetime.now(UTC),
            poam_required="false",
        )
        db.add(assessment)
        await db.commit()
        return {
            "linked": True,
            "evidence_id": evidence_id,
            "control_id": control_id,
            "assessment_id": assessment.id,
            "action": "created",
        }

    # Append evidence_id to existing assessment if not already present
    existing_ids: list = list(assessment.evidence_ids or [])
    if evidence_id in existing_ids:
        return {
            "linked": False,
            "evidence_id": evidence_id,
            "control_id": control_id,
            "assessment_id": assessment.id,
            "action": "already_linked",
        }

    existing_ids.append(evidence_id)
    assessment.evidence_ids = existing_ids
    await db.commit()
    return {
        "linked": True,
        "evidence_id": evidence_id,
        "control_id": control_id,
        "assessment_id": assessment.id,
        "action": "linked",
    }
