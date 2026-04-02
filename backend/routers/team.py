"""
Enterprise Team Tracking Dashboard Router
AGI Corporation 2026

Provides endpoints for managing team members, assigning CMMC controls to owners,
and rendering an enterprise compliance dashboard showing per-member posture,
domain rollups, overdue items, and a full control-owner responsibility matrix.
"""

import uuid
from datetime import UTC, datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (
    AssessmentRecord,
    ControlAssignment,
    ControlRecord,
    TeamMember,
    get_db,
    get_latest_assessments,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIORITY_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1}

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

VALID_ROLES = {
    "ISSO",
    "ISSM",
    "System Owner",
    "Control Owner",
    "Assessor",
    "C3PAO",
    "Security Engineer",
    "Network Engineer",
    "Developer",
    "Manager",
    "Other",
}

VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_ASSIGNMENT_STATUSES = {"open", "in_progress", "completed", "overdue"}
VALID_ASSIGNMENT_ROLES = {"owner", "reviewer", "approver"}


class TeamMemberCreate(BaseModel):
    name: str
    email: str
    role: str
    department: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


class ControlAssignmentCreate(BaseModel):
    member_id: str
    control_id: str
    role: str = "owner"
    due_date: Optional[datetime] = None
    priority: str = "medium"
    notes: Optional[str] = None


class ControlAssignmentUpdate(BaseModel):
    role: Optional[str] = None
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _compliance_status_weight(status: str) -> float:
    """Return a 0-1 compliance weight for a control status."""
    return {
        "implemented": 1.0,
        "partial": 0.5,
        "partially_implemented": 0.5,
        "planned": 0.25,
        "not_implemented": 0.0,
        "not_started": 0.0,
        "na": 1.0,
        "not_applicable": 1.0,
    }.get(status, 0.0)


def _assignment_overdue(assignment: ControlAssignment) -> bool:
    """Return True if an open/in_progress assignment is past its due date."""
    if assignment.status in ("completed",):
        return False
    if assignment.due_date and assignment.due_date < datetime.now(UTC):
        return True
    return False


def _serialize_member(m: TeamMember) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "email": m.email,
        "role": m.role,
        "department": m.department,
        "phone": m.phone,
        "active": bool(m.active),
        "notes": m.notes,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _serialize_assignment(a: ControlAssignment, assessments_map: dict = None, control: ControlRecord = None) -> dict:
    overdue = _assignment_overdue(a)
    effective_status = "overdue" if overdue and a.status != "completed" else a.status
    result = {
        "id": a.id,
        "member_id": a.member_id,
        "control_id": a.control_id,
        "role": a.role,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "completion_date": a.completion_date.isoformat() if a.completion_date else None,
        "priority": a.priority,
        "status": effective_status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
    if assessments_map is not None and a.control_id in assessments_map:
        ar = assessments_map[a.control_id]
        result["compliance_status"] = ar.status
        result["confidence"] = ar.confidence
    else:
        result["compliance_status"] = "not_started"
        result["confidence"] = 0.0

    if control:
        result["control_title"] = control.title
        result["domain"] = control.domain
        result["level"] = control.level
        result["zt_pillar"] = control.zt_pillar

    return result


# ---------------------------------------------------------------------------
# Team Member endpoints
# ---------------------------------------------------------------------------


@router.post("/members", summary="Create a new team member", status_code=201)
async def create_team_member(
    payload: TeamMemberCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new compliance team member."""
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{payload.role}'. Valid roles: {sorted(VALID_ROLES)}",
        )

    # Enforce unique email
    existing = await db.execute(
        select(TeamMember).where(TeamMember.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"A team member with email '{payload.email}' already exists.",
        )

    member = TeamMember(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        role=payload.role,
        department=payload.department,
        phone=payload.phone,
        notes=payload.notes,
        active=1,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return _serialize_member(member)


@router.get("/members", summary="List all team members with compliance stats")
async def list_team_members(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Return all team members enriched with their assignment and compliance stats."""
    query = select(TeamMember)
    if active_only:
        query = query.where(TeamMember.active == 1)
    result = await db.execute(query)
    members = result.scalars().all()

    # Fetch all assignments
    asgn_result = await db.execute(select(ControlAssignment))
    all_assignments = asgn_result.scalars().all()

    # Build member → assignments index
    member_assignments: Dict[str, list] = {}
    for a in all_assignments:
        member_assignments.setdefault(a.member_id, []).append(a)

    # Fetch latest assessments for enrichment
    assessments_map = await get_latest_assessments(db)

    members_out = []
    for m in members:
        assignments = member_assignments.get(m.id, [])
        total = len(assignments)
        completed = sum(1 for a in assignments if a.status == "completed")
        overdue = sum(1 for a in assignments if _assignment_overdue(a))
        in_progress = sum(1 for a in assignments if a.status == "in_progress")

        # Compliance score: average weight of controls they own
        weights = [
            _compliance_status_weight(
                assessments_map[a.control_id].status
                if a.control_id in assessments_map
                else "not_started"
            )
            for a in assignments
        ]
        compliance_pct = (sum(weights) / len(weights) * 100) if weights else None

        entry = _serialize_member(m)
        entry["stats"] = {
            "total_assigned": total,
            "completed": completed,
            "in_progress": in_progress,
            "overdue": overdue,
            "open": total - completed - in_progress,
            "compliance_pct": round(compliance_pct, 1) if compliance_pct is not None else None,
        }
        members_out.append(entry)

    return {"total": len(members_out), "members": members_out}


@router.get("/members/{member_id}", summary="Get team member detail with assigned controls")
async def get_team_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a team member with the full list of their control assignments and compliance status."""
    result = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail=f"Team member '{member_id}' not found.")

    asgn_result = await db.execute(
        select(ControlAssignment).where(ControlAssignment.member_id == member_id)
    )
    assignments = asgn_result.scalars().all()

    # Fetch controls + assessments for enrichment
    control_ids = [a.control_id for a in assignments]
    assessments_map = await get_latest_assessments(db, control_ids=control_ids if control_ids else None)

    controls_result = await db.execute(select(ControlRecord))
    controls_map = {c.id: c for c in controls_result.scalars().all()}

    serialized = [
        _serialize_assignment(a, assessments_map, controls_map.get(a.control_id))
        for a in assignments
    ]

    overdue_count = sum(1 for a in assignments if _assignment_overdue(a))
    weights = [
        _compliance_status_weight(
            assessments_map[a.control_id].status
            if a.control_id in assessments_map
            else "not_started"
        )
        for a in assignments
    ]
    compliance_pct = (sum(weights) / len(weights) * 100) if weights else None

    out = _serialize_member(member)
    out["stats"] = {
        "total_assigned": len(assignments),
        "completed": sum(1 for a in assignments if a.status == "completed"),
        "in_progress": sum(1 for a in assignments if a.status == "in_progress"),
        "overdue": overdue_count,
        "open": sum(1 for a in assignments if a.status == "open"),
        "compliance_pct": round(compliance_pct, 1) if compliance_pct is not None else None,
    }
    out["assignments"] = serialized
    return out


@router.patch("/members/{member_id}", summary="Update a team member")
async def update_team_member(
    member_id: str,
    payload: TeamMemberUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update team member fields."""
    result = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail=f"Team member '{member_id}' not found.")

    if payload.role is not None and payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{payload.role}'. Valid roles: {sorted(VALID_ROLES)}",
        )

    if payload.name is not None:
        member.name = payload.name
    if payload.email is not None:
        member.email = payload.email
    if payload.role is not None:
        member.role = payload.role
    if payload.department is not None:
        member.department = payload.department
    if payload.phone is not None:
        member.phone = payload.phone
    if payload.active is not None:
        member.active = 1 if payload.active else 0
    if payload.notes is not None:
        member.notes = payload.notes

    member.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(member)
    return _serialize_member(member)


@router.delete("/members/{member_id}", summary="Deactivate (soft-delete) a team member")
async def deactivate_team_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a team member by marking them inactive."""
    result = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail=f"Team member '{member_id}' not found.")

    member.active = 0
    member.updated_at = datetime.now(UTC)
    await db.commit()
    return {"status": "deactivated", "member_id": member_id}


# ---------------------------------------------------------------------------
# Control assignment endpoints
# ---------------------------------------------------------------------------


@router.post("/assignments", summary="Assign a CMMC control to a team member", status_code=201)
async def create_assignment(
    payload: ControlAssignmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Assign a specific CMMC control to a team member with optional due date and priority."""
    # Validate member exists
    member_result = await db.execute(select(TeamMember).where(TeamMember.id == payload.member_id))
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Team member '{payload.member_id}' not found.")

    # Validate control exists
    ctrl_result = await db.execute(select(ControlRecord).where(ControlRecord.id == payload.control_id))
    control = ctrl_result.scalar_one_or_none()
    if not control:
        raise HTTPException(status_code=404, detail=f"Control '{payload.control_id}' not found.")

    if payload.role not in VALID_ASSIGNMENT_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid assignment role '{payload.role}'. Valid: {sorted(VALID_ASSIGNMENT_ROLES)}",
        )
    if payload.priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid priority '{payload.priority}'. Valid: {sorted(VALID_PRIORITIES)}",
        )

    assignment = ControlAssignment(
        id=str(uuid.uuid4()),
        member_id=payload.member_id,
        control_id=payload.control_id,
        role=payload.role,
        due_date=payload.due_date,
        priority=payload.priority,
        status="open",
        notes=payload.notes,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    assessments_map = await get_latest_assessments(db, control_ids=[payload.control_id])
    return _serialize_assignment(assignment, assessments_map, control)


@router.patch("/assignments/{assignment_id}", summary="Update a control assignment")
async def update_assignment(
    assignment_id: str,
    payload: ControlAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update status, due date, priority, or notes on a control assignment."""
    result = await db.execute(
        select(ControlAssignment).where(ControlAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail=f"Assignment '{assignment_id}' not found.")

    if payload.role is not None:
        if payload.role not in VALID_ASSIGNMENT_ROLES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid role '{payload.role}'. Valid: {sorted(VALID_ASSIGNMENT_ROLES)}",
            )
        assignment.role = payload.role
    if payload.due_date is not None:
        assignment.due_date = payload.due_date
    if payload.completion_date is not None:
        assignment.completion_date = payload.completion_date
    if payload.priority is not None:
        if payload.priority not in VALID_PRIORITIES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid priority '{payload.priority}'. Valid: {sorted(VALID_PRIORITIES)}",
            )
        assignment.priority = payload.priority
    if payload.status is not None:
        if payload.status not in VALID_ASSIGNMENT_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{payload.status}'. Valid: {sorted(VALID_ASSIGNMENT_STATUSES)}",
            )
        assignment.status = payload.status
    if payload.notes is not None:
        assignment.notes = payload.notes

    assignment.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(assignment)

    assessments_map = await get_latest_assessments(db, control_ids=[assignment.control_id])
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == assignment.control_id)
    )
    control = ctrl_result.scalar_one_or_none()
    return _serialize_assignment(assignment, assessments_map, control)


@router.delete("/assignments/{assignment_id}", summary="Remove a control assignment")
async def delete_assignment(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a control assignment from a team member."""
    result = await db.execute(
        select(ControlAssignment).where(ControlAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail=f"Assignment '{assignment_id}' not found.")

    await db.delete(assignment)
    await db.commit()
    return {"status": "deleted", "assignment_id": assignment_id}


# ---------------------------------------------------------------------------
# Enterprise Dashboard endpoint
# ---------------------------------------------------------------------------


@router.get("/dashboard", summary="Enterprise team compliance dashboard")
async def get_team_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """
    Full enterprise compliance dashboard.

    Returns:
    - Organisation-wide compliance summary (SPRS, % implemented, readiness)
    - Per-domain compliance with owner breakdown
    - Per-member compliance posture ranked by gap exposure
    - Overdue assignments alert list
    - Unowned controls (no assignments yet)
    """
    # Load everything we need
    controls_result = await db.execute(select(ControlRecord))
    controls = controls_result.scalars().all()
    controls_map = {c.id: c for c in controls}

    assessments_map = await get_latest_assessments(db)

    members_result = await db.execute(select(TeamMember).where(TeamMember.active == 1))
    members = members_result.scalars().all()
    members_map = {m.id: m for m in members}

    asgn_result = await db.execute(select(ControlAssignment))
    all_assignments = asgn_result.scalars().all()

    # Index: control → assignments
    control_to_assignments: Dict[str, list] = {}
    member_to_assignments: Dict[str, list] = {}
    for a in all_assignments:
        control_to_assignments.setdefault(a.control_id, []).append(a)
        member_to_assignments.setdefault(a.member_id, []).append(a)

    # ── Organisation-wide compliance ──────────────────────────────────────────
    status_counts: Dict[str, int] = {
        "implemented": 0,
        "partial": 0,
        "planned": 0,
        "not_implemented": 0,
        "na": 0,
        "not_started": 0,
    }
    sprs = 110
    # SPRS point deductions per NIST SP 800-171 / DoD assessment methodology.
    # High-value controls (Level 2/3) deduct 5 points each; Level 1 controls deduct 3.
    # Default for any unlisted control is 1 point.  Maximum score is 110; floor is -203.
    SPRS_DEDUCTIONS = {
        "AC.2.006": 5, "AC.2.007": 5, "AC.3.017": 5, "AC.3.018": 5,
        "IA.3.083": 5, "IA.3.084": 5, "SC.3.177": 5,
        "AC.1.001": 3, "AC.1.002": 3, "IA.1.076": 3, "IA.1.077": 3,
        "SC.1.175": 3, "SC.1.176": 3, "SI.1.210": 3, "SI.1.211": 3,
        "SI.1.212": 3, "SI.1.213": 3,
    }

    for c in controls:
        ar = assessments_map.get(c.id)
        status = ar.status if ar else "not_started"
        bucket = "partial" if status == "partially_implemented" else status
        if bucket in status_counts:
            status_counts[bucket] += 1
        else:
            status_counts["not_started"] += 1
        if status in ("not_implemented", "not_started", "partially_implemented", "partial"):
            sprs -= SPRS_DEDUCTIONS.get(c.id, 1)

    total_controls = len(controls)
    implemented_count = status_counts["implemented"]
    compliance_pct = round(implemented_count / total_controls * 100, 1) if total_controls else 0

    if compliance_pct >= 100:
        readiness = "Ready for Certification"
    elif compliance_pct >= 80:
        readiness = "Near Compliant - Minor Gaps"
    elif compliance_pct >= 60:
        readiness = "In Progress - Significant Gaps"
    else:
        readiness = "Early Stage - Major Remediation Needed"

    org_summary = {
        "total_controls": total_controls,
        "status_breakdown": status_counts,
        "compliance_pct": compliance_pct,
        "sprs_score": max(sprs, -203),
        "readiness": readiness,
        "assessed_controls": len(assessments_map),
        "unassigned_controls": sum(
            1 for c in controls if c.id not in control_to_assignments
        ),
    }

    # ── Per-domain summary with ownership ────────────────────────────────────
    domain_summary: Dict[str, dict] = {}
    for c in controls:
        domain = c.domain
        if domain not in domain_summary:
            domain_summary[domain] = {
                "domain": domain,
                "total": 0,
                "implemented": 0,
                "partial": 0,
                "not_implemented": 0,
                "not_started": 0,
                "compliance_pct": 0.0,
                "owners": [],
            }
        ds = domain_summary[domain]
        ds["total"] += 1

        ar = assessments_map.get(c.id)
        status = ar.status if ar else "not_started"
        if status == "implemented":
            ds["implemented"] += 1
        elif status in ("partial", "partially_implemented"):
            ds["partial"] += 1
        elif status == "not_implemented":
            ds["not_implemented"] += 1
        else:
            ds["not_started"] += 1

        for a in control_to_assignments.get(c.id, []):
            m = members_map.get(a.member_id)
            if m and m.name not in ds["owners"]:
                ds["owners"].append(m.name)

    for ds in domain_summary.values():
        ds["compliance_pct"] = (
            round(ds["implemented"] / ds["total"] * 100, 1) if ds["total"] else 0.0
        )

    # ── Per-member posture ────────────────────────────────────────────────────
    member_posture = []
    for m in members:
        assignments = member_to_assignments.get(m.id, [])
        weights = [
            _compliance_status_weight(
                assessments_map[a.control_id].status
                if a.control_id in assessments_map
                else "not_started"
            )
            for a in assignments
        ]
        overdue_items = [a for a in assignments if _assignment_overdue(a)]
        critical_open = [
            a for a in assignments
            if a.priority in ("critical", "high")
            and a.status not in ("completed",)
            and not _assignment_overdue(a)
        ]
        member_posture.append({
            "member_id": m.id,
            "name": m.name,
            "email": m.email,
            "role": m.role,
            "department": m.department,
            "total_assigned": len(assignments),
            "completed": sum(1 for a in assignments if a.status == "completed"),
            "in_progress": sum(1 for a in assignments if a.status == "in_progress"),
            "overdue": len(overdue_items),
            "critical_open": len(critical_open),
            "compliance_pct": round(sum(weights) / len(weights) * 100, 1) if weights else None,
            "overdue_controls": [a.control_id for a in overdue_items],
        })

    # Sort by overdue desc, then compliance_pct asc (most at risk first)
    member_posture.sort(
        key=lambda x: (-x["overdue"], x["compliance_pct"] or 0)
    )

    # ── Overdue assignments ───────────────────────────────────────────────────
    overdue_list = []
    now_utc = datetime.now(UTC)
    for a in all_assignments:
        if _assignment_overdue(a):
            m = members_map.get(a.member_id)
            ctrl = controls_map.get(a.control_id)
            overdue_list.append({
                "assignment_id": a.id,
                "control_id": a.control_id,
                "control_title": ctrl.title if ctrl else None,
                "domain": ctrl.domain if ctrl else None,
                "priority": a.priority,
                "member_id": a.member_id,
                "member_name": m.name if m else None,
                "member_email": m.email if m else None,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "days_overdue": (
                    (now_utc - a.due_date).days if a.due_date else None
                ),
                "compliance_status": (
                    assessments_map[a.control_id].status
                    if a.control_id in assessments_map
                    else "not_started"
                ),
            })

    overdue_list.sort(key=lambda x: x["days_overdue"] or 0, reverse=True)

    # ── Unowned controls ──────────────────────────────────────────────────────
    unowned = []
    for c in controls:
        if c.id not in control_to_assignments:
            ar = assessments_map.get(c.id)
            unowned.append({
                "control_id": c.id,
                "domain": c.domain,
                "level": c.level,
                "title": c.title,
                "zt_pillar": c.zt_pillar,
                "status": ar.status if ar else "not_started",
            })

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "org_summary": org_summary,
        "domain_summary": sorted(domain_summary.values(), key=lambda d: d["compliance_pct"]),
        "member_posture": member_posture,
        "overdue_assignments": overdue_list,
        "unowned_controls": unowned,
        "team_size": len(members),
    }


# ---------------------------------------------------------------------------
# Overdue assignments endpoint
# ---------------------------------------------------------------------------


@router.get("/overdue", summary="List all overdue control assignments")
async def get_overdue_assignments(
    db: AsyncSession = Depends(get_db),
):
    """Return all control assignments past their due date that are not yet completed."""
    asgn_result = await db.execute(select(ControlAssignment))
    all_assignments = asgn_result.scalars().all()

    members_result = await db.execute(select(TeamMember))
    members_map = {m.id: m for m in members_result.scalars().all()}

    controls_result = await db.execute(select(ControlRecord))
    controls_map = {c.id: c for c in controls_result.scalars().all()}

    assessments_map = await get_latest_assessments(db)

    now_utc = datetime.now(UTC)
    overdue = []
    for a in all_assignments:
        if not _assignment_overdue(a):
            continue
        m = members_map.get(a.member_id)
        ctrl = controls_map.get(a.control_id)
        overdue.append({
            "assignment_id": a.id,
            "control_id": a.control_id,
            "control_title": ctrl.title if ctrl else None,
            "domain": ctrl.domain if ctrl else None,
            "level": ctrl.level if ctrl else None,
            "zt_pillar": ctrl.zt_pillar if ctrl else None,
            "priority": a.priority,
            "member_id": a.member_id,
            "member_name": m.name if m else None,
            "member_email": m.email if m else None,
            "member_role": m.role if m else None,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "days_overdue": (now_utc - a.due_date).days if a.due_date else None,
            "compliance_status": (
                assessments_map[a.control_id].status
                if a.control_id in assessments_map
                else "not_started"
            ),
        })

    overdue.sort(key=lambda x: (-PRIORITY_WEIGHTS.get(x["priority"], 0), x["days_overdue"] or 0))

    return {"total_overdue": len(overdue), "overdue_assignments": overdue}


# ---------------------------------------------------------------------------
# Responsibility matrix endpoint
# ---------------------------------------------------------------------------


@router.get("/matrix", summary="Control-owner responsibility matrix")
async def get_responsibility_matrix(
    db: AsyncSession = Depends(get_db),
):
    """
    Return a full control × member responsibility matrix.

    Each row is a control; each column is a team member.
    Cell value is the assignment role (owner/reviewer/approver) or null if unassigned.
    Also includes the current compliance status for each control.
    """
    controls_result = await db.execute(select(ControlRecord))
    controls = controls_result.scalars().all()

    members_result = await db.execute(select(TeamMember).where(TeamMember.active == 1))
    members = members_result.scalars().all()

    asgn_result = await db.execute(select(ControlAssignment))
    all_assignments = asgn_result.scalars().all()

    assessments_map = await get_latest_assessments(db)

    # Build lookup: (control_id, member_id) → assignment role
    cell_map: Dict[tuple, str] = {}
    for a in all_assignments:
        cell_map[(a.control_id, a.member_id)] = a.role

    member_headers = [
        {"id": m.id, "name": m.name, "role": m.role, "department": m.department}
        for m in members
    ]

    rows = []
    for c in controls:
        ar = assessments_map.get(c.id)
        row = {
            "control_id": c.id,
            "domain": c.domain,
            "level": c.level,
            "title": c.title,
            "zt_pillar": c.zt_pillar,
            "compliance_status": ar.status if ar else "not_started",
            "confidence": ar.confidence if ar else 0.0,
            "assignments": {
                m.id: cell_map.get((c.id, m.id))
                for m in members
            },
        }
        rows.append(row)

    return {
        "members": member_headers,
        "controls": rows,
        "total_controls": len(controls),
        "total_members": len(members),
    }
