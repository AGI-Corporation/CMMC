"""
Evidence Management Router
AGI Corporation 2026

Handles CMMC evidence artifact CRUD - REST and MCP tool.
Evidence types: log, scan, policy, diagram, screenshot, report, configuration.
All evidence records include ZT pillar, capability ID, and control mappings.
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, UTC

from backend.db.database import get_db, EvidenceRecord
from backend.models.evidence import EvidenceCreate, EvidenceResponse, EvidenceListResponse
from agents.mistral_agent.agent import agent as mistral_agent
from pydantic import BaseModel

router = APIRouter()

class EvidenceReviewRequest(BaseModel):
    reviewer_notes: str
    status: str  # approved/rejected/needs_work

class EvidenceReviewResponse(BaseModel):
    evidence_id: str
    reviewer_notes: str
    ai_feedback: str
    status: str


@router.post("/", response_model=EvidenceResponse,
             summary="Upload evidence artifact for a CMMC control")
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


@router.get("/", response_model=EvidenceListResponse,
            summary="List all evidence artifacts")
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


@router.get("/{evidence_id}", response_model=EvidenceResponse,
            summary="Get a specific evidence artifact")
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


@router.post("/{evidence_id}/review", response_model=EvidenceReviewResponse, summary="Review evidence artifact with AI feedback")
async def review_evidence(
    evidence_id: str,
    review: EvidenceReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Review an artifact and get automated AI feedback from Mistral."""
    result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")

    # Call Mistral for feedback
    context = f"Evidence Title: {record.title}\nDescription: {record.description}\nControl ID: {record.control_id}\nReviewer Status: {review.status}\nReviewer Notes: {review.reviewer_notes}"
    ai_feedback = await mistral_agent.answer_compliance_question(
        "Evaluate this evidence artifact and the reviewer's comments. Provide 2-3 bullet points of constructive feedback or next steps.",
        context=context
    )

    # Update record
    record.reviewer = "Human + Mistral"
    record.metadata_ = {**(record.metadata_ or {}), "ai_feedback": ai_feedback, "review_status": review.status, "reviewer_notes": review.reviewer_notes}
    await db.commit()

    return EvidenceReviewResponse(
        evidence_id=evidence_id,
        reviewer_notes=review.reviewer_notes,
        ai_feedback=ai_feedback,
        status=review.status
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
