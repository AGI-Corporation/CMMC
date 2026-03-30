"""
FHIR Evidence Ingestion Router
AGI Corporation 2026

Accepts FHIR R4 resources and automatically maps them to CMMC 2.0 controls,
creating EvidenceRecord entries so that healthcare system artifacts (AuditEvent,
Device, Consent, Observation, etc.) become first-class CMMC compliance evidence.

Endpoints:
  POST /api/fhir/ingest          - Ingest any mapped FHIR R4 resource
  POST /api/fhir/audit-event     - Shortcut for FHIR AuditEvent (AU domain)
  GET  /api/fhir/mappings        - List all FHIR→CMMC mappings
  GET  /api/fhir/mappings/{type} - Lookup mapping for a specific resource type

The optional BabelFHIR-TS sidecar (fhir-service/) validates resources before
ingestion when FHIR_VALIDATOR_URL is set.  Validation failures are surfaced as
422 responses; set FHIR_VALIDATOR_STRICT=false to degrade gracefully to warnings.
"""

import os
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import EvidenceRecord, get_db
from backend.services.fhir_service import (all_mappings, get_mapping,
                                            fhir_resource_to_evidence_payload)

router = APIRouter()

# ─── Optional BabelFHIR-TS sidecar config ─────────────────────────────────────
_VALIDATOR_URL = os.getenv("FHIR_VALIDATOR_URL", "").rstrip("/")
_VALIDATOR_STRICT = os.getenv("FHIR_VALIDATOR_STRICT", "true").lower() == "true"


# ─── Pydantic models ───────────────────────────────────────────────────────────


class FhirIngestRequest(BaseModel):
    """Request body for POST /api/fhir/ingest."""

    resource: Dict[str, Any] = Field(
        ...,
        description="A valid FHIR R4 resource object (must include 'resourceType').",
        json_schema_extra={
            "example": {
                "resourceType": "AuditEvent",
                "id": "ae-001",
                "type": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "110100"},
                "action": "R",
                "recorded": "2026-01-15T14:30:00Z",
                "outcome": "0",
                "agent": [{"who": {"reference": "Practitioner/prac-001"}, "requestor": True}],
                "source": {"observer": {"reference": "Device/ehr-server"}},
                "entity": [{"what": {"reference": "Patient/pat-001"}}],
            }
        },
    )
    control_id: Optional[str] = Field(
        None,
        description="Override: map only to this CMMC control ID instead of all defaults.",
        json_schema_extra={"example": "AU.2.041"},
    )
    reviewer: Optional[str] = Field(None, description="Name/ID of the evidence reviewer.")
    uri: Optional[str] = Field(None, description="Canonical URI of the FHIR resource.")


class FhirIngestResponse(BaseModel):
    """Response from POST /api/fhir/ingest."""

    fhir_resource_type: str
    fhir_resource_id: Optional[str]
    evidence_ids: List[str]
    cmmc_controls_covered: List[str]
    validation_status: str  # "validated" | "skipped" | "warning"
    validation_warnings: List[str]


class FhirMappingInfo(BaseModel):
    """One row in the mapping table."""

    fhir_resource_type: str
    control_ids: List[str]
    zt_pillar: str
    evidence_type: str
    rationale: str


# ─── Helpers ───────────────────────────────────────────────────────────────────


async def _validate_with_sidecar(
    resource: Dict[str, Any],
) -> tuple[str, List[str]]:
    """
    Call the BabelFHIR-TS sidecar validator if FHIR_VALIDATOR_URL is set.

    Returns (status, warnings) where status is one of:
      "validated" - sidecar confirmed the resource is valid
      "skipped"   - sidecar URL not configured
      "warning"   - sidecar returned warnings but not a hard failure
    """
    if not _VALIDATOR_URL:
        return "skipped", []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_VALIDATOR_URL}/validate",
                json=resource,
                headers={"Content-Type": "application/fhir+json"},
            )
        if resp.status_code == 200:
            body = resp.json()
            warnings = body.get("warnings", [])
            return ("validated" if not warnings else "warning"), warnings

        if resp.status_code == 422:
            body = resp.json()
            errors = body.get("errors", [resp.text])
            if _VALIDATOR_STRICT:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "FHIR resource failed BabelFHIR-TS validation.",
                        "errors": errors,
                    },
                )
            return "warning", errors

    except httpx.RequestError as exc:
        # Sidecar unreachable — degrade gracefully
        return "warning", [f"FHIR validator unreachable: {exc}"]

    return "skipped", []


def _persist_evidence(
    db: AsyncSession,
    payload: Dict[str, Any],
) -> EvidenceRecord:
    """
    Create and add an EvidenceRecord to the async session.

    `session.add()` is synchronous in SQLAlchemy's AsyncSession — only
    I/O-bound operations (execute, flush, commit) require awaiting.
    The caller is responsible for awaiting db.flush() / db.commit().
    """
    record = EvidenceRecord(
        id=str(uuid.uuid4()),
        control_id=payload["control_id"],
        zt_pillar=payload["zt_pillar"],
        zt_capability_id=payload.get("zt_capability_id"),
        evidence_type=payload["evidence_type"],
        title=payload["title"],
        description=payload["description"],
        source_system=payload["source_system"],
        uri=payload.get("uri"),
        reviewer=payload.get("reviewer"),
        review_cycle_days=payload.get("review_cycle_days", 365),
        metadata_=payload.get("metadata", {}),
        created_at=datetime.now(UTC),
    )
    db.add(record)
    return record


# ─── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/ingest",
    response_model=FhirIngestResponse,
    summary="Ingest a FHIR R4 resource as CMMC evidence",
    description=(
        "Accepts any FHIR R4 resource (AuditEvent, Device, Consent, etc.), "
        "optionally validates it via the BabelFHIR-TS sidecar, then creates "
        "EvidenceRecord entries linked to the appropriate CMMC control IDs."
    ),
)
async def ingest_fhir_resource(
    body: FhirIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> FhirIngestResponse:
    resource = body.resource
    resource_type = resource.get("resourceType")
    if not resource_type:
        raise HTTPException(
            status_code=400, detail="FHIR resource must include 'resourceType'."
        )

    mapping = get_mapping(resource_type)
    if not mapping and not body.control_id:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No CMMC mapping found for FHIR resourceType '{resource_type}'. "
                "Provide a 'control_id' override or use a supported resource type. "
                f"Supported types: {sorted(all_mappings().keys())}"
            ),
        )

    # Optional validation via BabelFHIR-TS sidecar
    validation_status, warnings = await _validate_with_sidecar(resource)

    # Build and persist evidence records
    try:
        payloads = fhir_resource_to_evidence_payload(
            resource,
            control_id=body.control_id,
            reviewer=body.reviewer,
            uri=body.uri,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    evidence_ids = []
    for payload in payloads:
        record = _persist_evidence(db, payload)
        evidence_ids.append(record.id)

    await db.flush()

    controls_covered = list({p["control_id"] for p in payloads})
    controls_covered.sort()

    return FhirIngestResponse(
        fhir_resource_type=resource_type,
        fhir_resource_id=resource.get("id"),
        evidence_ids=evidence_ids,
        cmmc_controls_covered=controls_covered,
        validation_status=validation_status,
        validation_warnings=warnings,
    )


@router.post(
    "/audit-event",
    response_model=FhirIngestResponse,
    summary="Ingest a FHIR AuditEvent as AU-domain CMMC evidence",
    description=(
        "Convenience endpoint for FHIR AuditEvent resources. Maps to AU.2.041, "
        "AU.2.042, AU.2.043, AU.3.045, AU.3.046, and AU.3.048 (Audit & "
        "Accountability domain). Equivalent to POST /ingest with resourceType=AuditEvent."
    ),
)
async def ingest_audit_event(
    body: FhirIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> FhirIngestResponse:
    resource = body.resource
    # Enforce AuditEvent resource type on this dedicated endpoint
    if resource.get("resourceType") and resource["resourceType"] != "AuditEvent":
        raise HTTPException(
            status_code=400,
            detail=(
                f"This endpoint only accepts AuditEvent resources; "
                f"got '{resource['resourceType']}'. Use POST /ingest instead."
            ),
        )
    resource["resourceType"] = "AuditEvent"
    body.resource = resource
    return await ingest_fhir_resource(body, db)


@router.get(
    "/mappings",
    response_model=List[FhirMappingInfo],
    summary="List all FHIR → CMMC control mappings",
    description=(
        "Returns the complete table of supported FHIR R4 resource types and "
        "the CMMC 2.0 controls they map to. Use this to understand which FHIR "
        "resources can be ingested as compliance evidence."
    ),
)
async def list_fhir_mappings() -> List[FhirMappingInfo]:
    return [
        FhirMappingInfo(
            fhir_resource_type=resource_type,
            control_ids=info["control_ids"],
            zt_pillar=info["zt_pillar"],
            evidence_type=info["evidence_type"],
            rationale=info["rationale"],
        )
        for resource_type, info in sorted(all_mappings().items())
    ]


@router.get(
    "/mappings/{resource_type}",
    response_model=FhirMappingInfo,
    summary="Get CMMC mapping for a specific FHIR resource type",
    description=(
        "Returns the CMMC controls, ZT pillar, and rationale for a single "
        "FHIR R4 resource type (e.g., AuditEvent, Device, Consent)."
    ),
)
async def get_fhir_mapping(resource_type: str) -> FhirMappingInfo:
    mapping = get_mapping(resource_type)
    if not mapping:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No CMMC mapping found for FHIR resource type '{resource_type}'. "
                f"Supported types: {sorted(all_mappings().keys())}"
            ),
        )
    return FhirMappingInfo(
        fhir_resource_type=resource_type,
        control_ids=mapping["control_ids"],
        zt_pillar=mapping["zt_pillar"],
        evidence_type=mapping["evidence_type"],
        rationale=mapping["rationale"],
    )
