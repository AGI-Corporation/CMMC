"""
CMMC Controls Router - FastAPI endpoints for control management.
These endpoints are automatically exposed as MCP tools via fastapi-mcp.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import json
import os

from backend.models.control import (
    Control, ControlResponse, ControlListResponse,
    ControlUpdate, CMMCLevel, ControlDomain, ImplementationStatus
)

router = APIRouter()

# In-memory store for assessment status (replace with DB in production)
_assessment_store: dict = {}


def load_controls() -> List[dict]:
    """Load CMMC controls from OSCAL JSON schema."""
    schema_path = os.getenv("OSCAL_CATALOG_PATH", "./schema/cmmc_oscal_catalog.json")
    if os.path.exists(schema_path):
        with open(schema_path) as f:
            data = json.load(f)
            return data.get("controls", [])
    return []


@router.get(
    "/",
    response_model=ControlListResponse,
    summary="List CMMC Controls",
    description="List all CMMC controls, optionally filtered by level or domain. Returns controls with current implementation status."
)
async def list_controls(
    level: Optional[CMMCLevel] = Query(None, description="Filter by CMMC level (Level 1, Level 2, Level 3)"),
    domain: Optional[ControlDomain] = Query(None, description="Filter by control domain (AC, AU, CM, etc.)"),
    status: Optional[ImplementationStatus] = Query(None, description="Filter by implementation status")
):
    controls_data = load_controls()
    responses = []
    for c in controls_data:
        if level and c.get("level") != level.value:
            continue
        if domain and c.get("domain") != domain.value:
            continue
        impl_status = _assessment_store.get(c["id"], {}).get("status")
        if status and impl_status != status.value:
            continue
        responses.append(ControlResponse(
            control=Control(**c),
            implementation_status=impl_status,
            evidence_count=_assessment_store.get(c["id"], {}).get("evidence_count", 0),
            notes=_assessment_store.get(c["id"], {}).get("notes")
        ))
    return ControlListResponse(controls=responses, total=len(responses), level_filter=level, domain_filter=domain)


@router.get(
    "/{control_id}",
    response_model=ControlResponse,
    summary="Get Control Detail",
    description="Get full details of a specific CMMC control by its ID (e.g., AC.1.001)."
)
async def get_control_detail(control_id: str):
    controls_data = load_controls()
    for c in controls_data:
        if c["id"] == control_id:
            return ControlResponse(
                control=Control(**c),
                implementation_status=_assessment_store.get(control_id, {}).get("status"),
                evidence_count=_assessment_store.get(control_id, {}).get("evidence_count", 0),
                notes=_assessment_store.get(control_id, {}).get("notes")
            )
    raise HTTPException(status_code=404, detail=f"Control {control_id} not found")


@router.patch(
    "/{control_id}",
    response_model=ControlResponse,
    summary="Update Control Assessment Status",
    description="Update the implementation status, notes, and responsible party for a CMMC control."
)
async def update_control_status(control_id: str, update: ControlUpdate):
    controls_data = load_controls()
    control = next((c for c in controls_data if c["id"] == control_id), None)
    if not control:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
    _assessment_store[control_id] = {
        "status": update.implementation_status.value,
        "notes": update.notes,
        "responsible_party": update.responsible_party,
        "target_completion_date": str(update.target_completion_date) if update.target_completion_date else None,
        "evidence_count": _assessment_store.get(control_id, {}).get("evidence_count", 0)
    }
    return ControlResponse(
        control=Control(**control),
        implementation_status=update.implementation_status,
        notes=update.notes
    )


@router.get(
    "/domain/{domain}",
    response_model=ControlListResponse,
    summary="Get Controls by Domain",
    description="Get all CMMC controls for a specific domain (e.g., AC for Access Control)."
)
async def get_controls_by_domain(domain: ControlDomain):
    return await list_controls(domain=domain)
