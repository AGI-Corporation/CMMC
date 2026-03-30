"""
FHIR Service - FHIR resource parsing and CMMC control mapping.
AGI Corporation 2026

Maps FHIR R4 resources (AuditEvent, Device, Consent, Observation, etc.) to
CMMC 2.0 control domains so that healthcare-system artifacts can serve as
machine-readable compliance evidence.

References:
  - FHIR R4 AuditEvent: https://hl7.org/fhir/R4/auditevent.html
  - NIST SP 800-171 Rev 2 control families: AU, AC, IA, CM, RA, SC, SI
  - BabelFHIR-TS sidecar: fhir-service/ (TypeScript, uses @babelfhir-ts/client-r4)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

# ─── FHIR → CMMC control mapping ─────────────────────────────────────────────
# Each entry maps a FHIR R4 resource type to a list of CMMC control IDs it can
# serve as evidence for, plus the relevant Zero-Trust pillar.

FHIR_CMMC_MAP: Dict[str, Dict[str, Any]] = {
    # ── Audit & Accountability ──────────────────────────────────────────────
    "AuditEvent": {
        "control_ids": [
            "AU.2.041",  # Create and retain system audit logs
            "AU.2.042",  # Ensure individual accountability through unique IDs
            "AU.2.043",  # Review and analyze audit records
            "AU.3.045",  # Analyze and report audit anomalies
            "AU.3.046",  # Protect audit information from unauthorized access
            "AU.3.048",  # Collect audit info into central repositories
        ],
        "zt_pillar": "Visibility & Analytics",
        "evidence_type": "log",
        "rationale": (
            "FHIR AuditEvent is the healthcare-native mechanism for recording "
            "who accessed which resource, when, and from where—directly "
            "satisfying NIST AU-2/AU-3 logging and accountability requirements."
        ),
    },
    "DocumentReference": {
        "control_ids": ["AU.3.046", "AU.3.048"],
        "zt_pillar": "Visibility & Analytics",
        "evidence_type": "log",
        "rationale": (
            "DocumentReference resources pointing to audit logs or policy "
            "documents support log-retention and protection controls."
        ),
    },
    # ── Access Control ──────────────────────────────────────────────────────
    "Consent": {
        "control_ids": ["AC.2.006", "AC.2.007", "AC.3.018"],
        "zt_pillar": "User",
        "evidence_type": "policy",
        "rationale": (
            "FHIR Consent resources document patient-level access grants and "
            "restrictions, evidencing least-privilege and CUI-flow controls."
        ),
    },
    "Patient": {
        "control_ids": ["AC.1.001", "AC.1.002"],
        "zt_pillar": "User",
        "evidence_type": "configuration",
        "rationale": (
            "Patient resources carry the identity context used to enforce "
            "authorized-access and transaction-type limitations."
        ),
    },
    # ── Identification & Authentication ─────────────────────────────────────
    "Practitioner": {
        "control_ids": ["IA.1.076", "IA.1.077", "IA.3.083"],
        "zt_pillar": "User",
        "evidence_type": "configuration",
        "rationale": (
            "Practitioner resources carry credential and role data needed to "
            "verify identification and authentication of healthcare workforce."
        ),
    },
    "PractitionerRole": {
        "control_ids": ["IA.1.076", "IA.1.077", "AC.2.007"],
        "zt_pillar": "User",
        "evidence_type": "configuration",
        "rationale": (
            "PractitionerRole narrows access grants to a specific "
            "organizational role, supporting least-privilege and "
            "identification controls."
        ),
    },
    # ── Configuration Management ─────────────────────────────────────────────
    "Device": {
        "control_ids": ["CM.2.061", "CM.2.062", "CM.3.068"],
        "zt_pillar": "Device",
        "evidence_type": "configuration",
        "rationale": (
            "FHIR Device resources enumerate medical IoT endpoints that must "
            "appear in the configuration baseline and software inventory."
        ),
    },
    # ── Risk Assessment ──────────────────────────────────────────────────────
    "Observation": {
        "control_ids": ["RA.2.141", "RA.2.142"],
        "zt_pillar": "Visibility & Analytics",
        "evidence_type": "scan",
        "rationale": (
            "Security-related Observation resources (e.g., vulnerability "
            "scan results or anomaly flags) serve as machine-readable "
            "risk-assessment artifacts."
        ),
    },
    # ── System & Communications Protection ──────────────────────────────────
    "Communication": {
        "control_ids": ["SC.1.175", "SC.1.176", "SC.3.177"],
        "zt_pillar": "Network",
        "evidence_type": "log",
        "rationale": (
            "FHIR Communication resources record data-exchange events and can "
            "evidence boundary-monitoring and encryption controls."
        ),
    },
    # ── System & Information Integrity ───────────────────────────────────────
    "OperationOutcome": {
        "control_ids": ["SI.1.210", "SI.1.211"],
        "zt_pillar": "Application",
        "evidence_type": "report",
        "rationale": (
            "OperationOutcome resources capture FHIR server error states and "
            "validation failures, supporting flaw-identification requirements."
        ),
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def get_mapping(resource_type: str) -> Optional[Dict[str, Any]]:
    """Return the CMMC mapping for a given FHIR resource type, or None."""
    return FHIR_CMMC_MAP.get(resource_type)


def all_mappings() -> Dict[str, Dict[str, Any]]:
    """Return the full FHIR→CMMC mapping table."""
    return FHIR_CMMC_MAP


# ─── AuditEvent extraction ────────────────────────────────────────────────────


def extract_audit_event_metadata(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract compliance-relevant fields from a FHIR R4 AuditEvent resource.

    Returns a dict with:
      - action     : C/R/U/D/E (FHIR AuditEvent.action)
      - outcome    : 0/4/8/12 → success/minor-failure/serious-failure/major-failure
      - recorded   : ISO-8601 timestamp
      - agent_who  : list of agent identifiers (practitioner references)
      - entity_refs: list of referenced resource identifiers
      - source_site: reporting site identifier
    """
    agents = resource.get("agent", [])
    agent_ids = []
    for a in agents:
        who = a.get("who", {})
        ref = who.get("reference") or who.get("identifier", {}).get("value")
        if ref:
            agent_ids.append(ref)

    entities = resource.get("entity", [])
    entity_refs = []
    for e in entities:
        what = e.get("what", {})
        ref = what.get("reference") or what.get("identifier", {}).get("value")
        if ref:
            entity_refs.append(ref)

    source = resource.get("source", {})
    site = source.get("site") or source.get("observer", {}).get("reference")

    return {
        "action": resource.get("action"),
        "outcome": resource.get("outcome"),
        "recorded": resource.get("recorded"),
        "agent_ids": agent_ids,
        "entity_refs": entity_refs,
        "source_site": site,
        "subtype": [
            c.get("code") for c in resource.get("subtype", []) if c.get("code")
        ],
    }


def build_evidence_title(resource: Dict[str, Any]) -> str:
    """Construct a human-readable evidence title from a FHIR resource."""
    resource_type = resource.get("resourceType", "Unknown")
    rid = resource.get("id", "")

    if resource_type == "AuditEvent":
        action = resource.get("action", "")
        recorded = resource.get("recorded", "")[:10] if resource.get("recorded") else ""
        return f"FHIR AuditEvent [{action}] recorded {recorded} (id={rid})"

    if resource_type == "Device":
        name_list = resource.get("deviceName", [])
        name = name_list[0].get("name", "") if name_list else ""
        return f"FHIR Device: {name or rid}"

    if resource_type == "Observation":
        code = resource.get("code", {}).get("text") or resource.get(
            "code", {}
        ).get("coding", [{}])[0].get("display", "")
        return f"FHIR Observation: {code or rid}"

    return f"FHIR {resource_type} (id={rid})"


def build_evidence_description(
    resource: Dict[str, Any], mapping: Dict[str, Any]
) -> str:
    """Build an evidence description that ties the FHIR resource to CMMC controls."""
    resource_type = resource.get("resourceType", "Unknown")
    controls = ", ".join(mapping.get("control_ids", []))
    rationale = mapping.get("rationale", "")
    rid = resource.get("id", "unspecified")

    lines = [
        f"FHIR {resource_type} resource (id={rid}) ingested as CMMC evidence.",
        f"Mapped controls: {controls}.",
        f"Rationale: {rationale}",
    ]

    if resource_type == "AuditEvent":
        meta = extract_audit_event_metadata(resource)
        if meta["agent_ids"]:
            lines.append(f"Agents: {', '.join(meta['agent_ids'][:5])}")
        if meta["entity_refs"]:
            lines.append(f"Entities accessed: {', '.join(meta['entity_refs'][:5])}")
        if meta["outcome"] is not None:
            outcome_label = {
                "0": "Success",
                "4": "Minor failure",
                "8": "Serious failure",
                "12": "Major failure",
            }.get(str(meta["outcome"]), f"outcome={meta['outcome']}")
            lines.append(f"Outcome: {outcome_label}")

    return " ".join(lines)


def fhir_resource_to_evidence_payload(
    resource: Dict[str, Any],
    control_id: Optional[str] = None,
    reviewer: Optional[str] = None,
    uri: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convert a FHIR R4 resource into one EvidenceCreate payload per mapped
    CMMC control (or a single payload for a specified control_id).

    Returns a list of dicts ready to be posted to POST /api/evidence/.
    """
    resource_type = resource.get("resourceType")
    if not resource_type:
        raise ValueError("FHIR resource is missing 'resourceType' field.")

    mapping = get_mapping(resource_type)
    if not mapping and not control_id:
        raise ValueError(
            f"No CMMC mapping found for FHIR resourceType '{resource_type}'. "
            "Provide an explicit control_id to override."
        )

    effective_mapping = mapping or {
        "control_ids": [control_id],
        "zt_pillar": "Visibility & Analytics",
        "evidence_type": "log",
        "rationale": "Manually specified control mapping.",
    }

    target_controls = (
        [control_id] if control_id else effective_mapping["control_ids"]
    )

    title = build_evidence_title(resource)
    description = build_evidence_description(resource, effective_mapping)
    source_system = f"FHIR/{resource_type}"

    payloads = []
    for cid in target_controls:
        payloads.append(
            {
                "control_id": cid,
                "zt_pillar": effective_mapping["zt_pillar"],
                "zt_capability_id": None,
                "evidence_type": effective_mapping["evidence_type"],
                "title": title,
                "description": description,
                "source_system": source_system,
                "uri": uri,
                "reviewer": reviewer,
                "review_cycle_days": 365,
                "metadata": {
                    "fhir_resource_type": resource_type,
                    "fhir_resource_id": resource.get("id"),
                    "fhir_version": "R4",
                    "ingested_at": datetime.now(UTC).isoformat(),
                },
            }
        )
    return payloads
