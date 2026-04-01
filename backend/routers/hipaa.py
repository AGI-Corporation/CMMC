"""
HIPAA Security Rule Overlay Router
AGI Corporation 2026

Maps HIPAA Security Rule safeguards (45 CFR 164.308–164.316) to CMMC 2.0
controls and evaluates where current CMMC compliance satisfies HIPAA requirements.

Use this overlay when the system processes Protected Health Information (PHI)
in addition to CUI — e.g., Max Health Inc. clinical data pipelines.

HIPAA Safeguard Categories:
  164.308 – Administrative Safeguards
  164.310 – Physical Safeguards
  164.312 – Technical Safeguards
  164.314 – Organizational Requirements
  164.316 – Policies, Procedures and Documentation
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import ControlRecord, get_db, get_latest_assessments

router = APIRouter()

# ─── HIPAA → CMMC control mapping ─────────────────────────────────────────────
# Each HIPAA specification is mapped to the CMMC controls that satisfy or
# partially satisfy the same requirement.  Confidence weight expresses how
# fully a CMMC implementation covers the HIPAA requirement (0.0–1.0).

HIPAA_TO_CMMC: List[Dict[str, Any]] = [
    # ── 164.308 Administrative Safeguards ──────────────────────────────────────
    {
        "hipaa_id": "164.308(a)(1)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Security Management Process",
        "description": "Implement policies and procedures to prevent, detect, contain, and correct security violations.",
        "required": True,
        "cmmc_controls": ["CA.2.157", "RA.2.141", "RA.2.142", "RA.3.144"],
        "cmmc_weight": 0.85,
        "gap_notes": "CMMC CA/RA domains satisfy risk analysis and security plan requirements.",
    },
    {
        "hipaa_id": "164.308(a)(2)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Assigned Security Responsibility",
        "description": "Identify the security official responsible for the development and implementation of policies and procedures.",
        "required": True,
        "cmmc_controls": ["CA.2.157", "CA.3.161"],
        "cmmc_weight": 0.90,
        "gap_notes": "SSP must name ISSO/HIPAA Security Officer explicitly.",
    },
    {
        "hipaa_id": "164.308(a)(3)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Workforce Security",
        "description": "Implement policies and procedures to ensure workforce members have appropriate access to ePHI.",
        "required": True,
        "cmmc_controls": ["AC.1.001", "AC.1.002", "AC.2.005", "AC.2.006", "PS.2.127"],
        "cmmc_weight": 0.90,
        "gap_notes": "CMMC AC domain covers access authorization and termination.",
    },
    {
        "hipaa_id": "164.308(a)(4)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Information Access Management",
        "description": "Implement policies and procedures for authorizing access to ePHI.",
        "required": True,
        "cmmc_controls": ["AC.2.006", "AC.2.007", "AC.3.017", "IA.1.076", "IA.1.077"],
        "cmmc_weight": 0.88,
        "gap_notes": "Role-based access and MFA controls satisfy access management.",
    },
    {
        "hipaa_id": "164.308(a)(5)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Security Awareness and Training",
        "description": "Implement a security awareness and training program for all members of the workforce.",
        "required": True,
        "cmmc_controls": ["AT.2.056", "AT.2.057", "AT.3.058"],
        "cmmc_weight": 0.85,
        "gap_notes": "CMMC AT domain provides awareness and role-based training requirements.",
    },
    {
        "hipaa_id": "164.308(a)(6)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Security Incident Procedures",
        "description": "Implement policies and procedures to address security incidents.",
        "required": True,
        "cmmc_controls": ["IR.2.092", "IR.2.093", "IR.2.094", "IR.3.098"],
        "cmmc_weight": 0.90,
        "gap_notes": "CMMC IR domain covers incident identification, response, and reporting.",
    },
    {
        "hipaa_id": "164.308(a)(7)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Contingency Plan",
        "description": "Establish policies and procedures for responding to an emergency or occurrence that damages PHI systems.",
        "required": True,
        "cmmc_controls": ["CP.2.004", "CP.2.008", "CP.3.012"],
        "cmmc_weight": 0.80,
        "gap_notes": "CMMC CP domain partially satisfies contingency planning; test documentation may require HIPAA-specific additions.",
    },
    {
        "hipaa_id": "164.308(a)(8)",
        "safeguard_category": "Administrative",
        "cfr_section": "164.308",
        "title": "Evaluation",
        "description": "Perform a periodic technical and non-technical evaluation in response to environmental or operational changes.",
        "required": True,
        "cmmc_controls": ["CA.2.157", "CA.2.158", "CA.3.161", "CA.3.162"],
        "cmmc_weight": 0.88,
        "gap_notes": "CMMC CA domain evaluation activities satisfy HIPAA periodic assessment requirement.",
    },
    # ── 164.310 Physical Safeguards ────────────────────────────────────────────
    {
        "hipaa_id": "164.310(a)(1)",
        "safeguard_category": "Physical",
        "cfr_section": "164.310",
        "title": "Facility Access Controls",
        "description": "Implement policies and procedures to limit physical access to electronic information systems and facilities.",
        "required": True,
        "cmmc_controls": ["PE.1.131", "PE.1.132", "PE.2.120", "PE.3.136"],
        "cmmc_weight": 0.90,
        "gap_notes": "CMMC PE domain covers physical access control requirements.",
    },
    {
        "hipaa_id": "164.310(b)",
        "safeguard_category": "Physical",
        "cfr_section": "164.310",
        "title": "Workstation Use",
        "description": "Implement policies and procedures that specify the proper functions to be performed and how these functions are to be performed.",
        "required": True,
        "cmmc_controls": ["AC.1.001", "CM.2.061", "CM.3.068"],
        "cmmc_weight": 0.75,
        "gap_notes": "CMMC controls address workstation function restrictions; HIPAA may require explicit workstation use policies.",
    },
    {
        "hipaa_id": "164.310(c)",
        "safeguard_category": "Physical",
        "cfr_section": "164.310",
        "title": "Workstation Security",
        "description": "Implement physical safeguards for all workstations that access ePHI.",
        "required": True,
        "cmmc_controls": ["PE.1.131", "PE.2.120", "CM.2.061"],
        "cmmc_weight": 0.80,
        "gap_notes": "Physical security controls satisfy workstation security requirements.",
    },
    {
        "hipaa_id": "164.310(d)(1)",
        "safeguard_category": "Physical",
        "cfr_section": "164.310",
        "title": "Device and Media Controls",
        "description": "Implement policies and procedures that govern the receipt and removal of hardware and electronic media.",
        "required": True,
        "cmmc_controls": ["MP.1.001", "MP.1.002", "MP.2.120", "MP.2.121", "MP.3.122"],
        "cmmc_weight": 0.90,
        "gap_notes": "CMMC MP domain covers media protection, sanitization, and transport controls.",
    },
    # ── 164.312 Technical Safeguards ───────────────────────────────────────────
    {
        "hipaa_id": "164.312(a)(1)",
        "safeguard_category": "Technical",
        "cfr_section": "164.312",
        "title": "Access Control",
        "description": "Implement technical policies and procedures for electronic information systems that maintain ePHI to allow access only to authorized persons.",
        "required": True,
        "cmmc_controls": ["AC.1.001", "AC.2.006", "AC.2.007", "IA.1.076", "IA.2.078", "IA.3.083"],
        "cmmc_weight": 0.92,
        "gap_notes": "CMMC AC and IA domains provide strong technical access control coverage.",
    },
    {
        "hipaa_id": "164.312(b)",
        "safeguard_category": "Technical",
        "cfr_section": "164.312",
        "title": "Audit Controls",
        "description": "Implement hardware, software, and procedural mechanisms that record and examine activity in systems containing ePHI.",
        "required": True,
        "cmmc_controls": ["AU.2.041", "AU.2.042", "AU.2.043", "AU.2.044", "AU.3.045"],
        "cmmc_weight": 0.90,
        "gap_notes": "CMMC AU domain audit logging and review requirements satisfy HIPAA audit controls.",
    },
    {
        "hipaa_id": "164.312(c)(1)",
        "safeguard_category": "Technical",
        "cfr_section": "164.312",
        "title": "Integrity",
        "description": "Implement policies and procedures to protect ePHI from improper alteration or destruction.",
        "required": True,
        "cmmc_controls": ["SI.1.210", "SI.1.211", "SC.3.177", "AU.2.041"],
        "cmmc_weight": 0.85,
        "gap_notes": "CMMC SI and SC controls address data integrity and protection from unauthorized modification.",
    },
    {
        "hipaa_id": "164.312(d)",
        "safeguard_category": "Technical",
        "cfr_section": "164.312",
        "title": "Person or Entity Authentication",
        "description": "Implement procedures to verify that a person seeking access to ePHI is the one claimed.",
        "required": True,
        "cmmc_controls": ["IA.1.076", "IA.1.077", "IA.2.078", "IA.2.079", "IA.3.083"],
        "cmmc_weight": 0.95,
        "gap_notes": "CMMC IA domain authentication requirements directly satisfy HIPAA authentication specification.",
    },
    {
        "hipaa_id": "164.312(e)(1)",
        "safeguard_category": "Technical",
        "cfr_section": "164.312",
        "title": "Transmission Security",
        "description": "Implement technical security measures to guard against unauthorized access to ePHI transmitted over an electronic communications network.",
        "required": True,
        "cmmc_controls": ["SC.1.175", "SC.1.176", "SC.3.177", "SC.3.187"],
        "cmmc_weight": 0.92,
        "gap_notes": "CMMC SC domain encryption-in-transit requirements satisfy HIPAA transmission security.",
    },
    # ── 164.314 Organizational Requirements ───────────────────────────────────
    {
        "hipaa_id": "164.314(a)(1)",
        "safeguard_category": "Organizational",
        "cfr_section": "164.314",
        "title": "Business Associate Contracts",
        "description": "A covered entity may permit a business associate to create, receive, maintain, or transmit ePHI only if the covered entity obtains satisfactory assurances.",
        "required": True,
        "cmmc_controls": ["CA.2.157", "PS.2.127"],
        "cmmc_weight": 0.60,
        "gap_notes": "CMMC controls partially cover; explicit BAA documentation required for HIPAA. Supply chain controls (SR domain) may apply.",
    },
    # ── 164.316 Policies, Procedures and Documentation ─────────────────────────
    {
        "hipaa_id": "164.316(a)",
        "safeguard_category": "Documentation",
        "cfr_section": "164.316",
        "title": "Policies and Procedures",
        "description": "Implement reasonable and appropriate policies and procedures to comply with the standards, implementation specifications, or other requirements of the Security Rule.",
        "required": True,
        "cmmc_controls": ["CA.2.157", "CA.3.161", "CA.3.162"],
        "cmmc_weight": 0.88,
        "gap_notes": "CMMC SSP and continuous monitoring satisfy HIPAA documentation requirements.",
    },
    {
        "hipaa_id": "164.316(b)(1)",
        "safeguard_category": "Documentation",
        "cfr_section": "164.316",
        "title": "Documentation Retention",
        "description": "Retain the documentation required for 6 years from the date of its creation or the date when it last was in effect.",
        "required": True,
        "cmmc_controls": ["AU.2.041", "AU.2.044", "CA.2.157"],
        "cmmc_weight": 0.75,
        "gap_notes": "CMMC audit retention may not meet HIPAA 6-year retention; verify log retention policy explicitly.",
    },
]


def _assess_hipaa_control(
    hipaa_ctrl: Dict[str, Any],
    assessments_map: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate a single HIPAA safeguard by looking at the implementation status
    of its mapped CMMC controls.
    """
    cmmc_ids = hipaa_ctrl["cmmc_controls"]
    weight = hipaa_ctrl["cmmc_weight"]

    implemented = 0
    partial = 0
    not_impl = 0
    total = len(cmmc_ids)
    missing_cmmc = []

    for cid in cmmc_ids:
        rec = assessments_map.get(cid)
        if rec is None:
            not_impl += 1
            missing_cmmc.append(cid)
        elif rec.status == "implemented":
            implemented += 1
        elif rec.status in ("partially_implemented", "partial"):
            partial += 1
        else:
            not_impl += 1
            missing_cmmc.append(cid)

    if total == 0:
        raw_score = 0.0
    else:
        raw_score = (implemented + 0.5 * partial) / total

    # Apply CMMC→HIPAA coverage weight
    hipaa_confidence = round(raw_score * weight, 2)

    if hipaa_confidence >= 0.85:
        hipaa_status = "satisfied"
    elif hipaa_confidence >= 0.50:
        hipaa_status = "partially_satisfied"
    else:
        hipaa_status = "gap"

    return {
        "hipaa_id": hipaa_ctrl["hipaa_id"],
        "cfr_section": hipaa_ctrl["cfr_section"],
        "safeguard_category": hipaa_ctrl["safeguard_category"],
        "title": hipaa_ctrl["title"],
        "required": hipaa_ctrl["required"],
        "hipaa_status": hipaa_status,
        "hipaa_confidence": hipaa_confidence,
        "cmmc_controls_mapped": cmmc_ids,
        "cmmc_controls_missing": missing_cmmc,
        "cmmc_controls_implemented": implemented,
        "cmmc_controls_partial": partial,
        "cmmc_controls_not_implemented": not_impl,
        "gap_notes": hipaa_ctrl["gap_notes"],
    }


# ─── Routes ───────────────────────────────────────────────────────────────────


@router.get(
    "/assess",
    summary="HIPAA Security Rule compliance assessment (CMMC overlay)",
)
async def assess_hipaa_compliance(db: AsyncSession = Depends(get_db)):
    """
    Evaluate HIPAA Security Rule (45 CFR Part 164) compliance by mapping each
    safeguard to its corresponding CMMC controls and checking implementation status.

    Returns per-safeguard status: satisfied / partially_satisfied / gap.
    """
    assessments_map = await get_latest_assessments(db)
    results = [_assess_hipaa_control(h, assessments_map) for h in HIPAA_TO_CMMC]

    satisfied = sum(1 for r in results if r["hipaa_status"] == "satisfied")
    partial = sum(1 for r in results if r["hipaa_status"] == "partially_satisfied")
    gap = sum(1 for r in results if r["hipaa_status"] == "gap")
    total = len(results)

    overall_pct = round((satisfied + 0.5 * partial) / total * 100, 1) if total else 0

    return {
        "framework": "HIPAA Security Rule (45 CFR 164.308–164.316)",
        "system": "AGI Corp / Max Health Inc.",
        "assessed_at": datetime.now(UTC).isoformat(),
        "total_safeguards": total,
        "satisfied": satisfied,
        "partially_satisfied": partial,
        "gap": gap,
        "overall_compliance_pct": overall_pct,
        "safeguards": results,
    }


@router.get(
    "/gaps",
    summary="List HIPAA gaps — safeguards not fully satisfied by current CMMC posture",
)
async def list_hipaa_gaps(db: AsyncSession = Depends(get_db)):
    """
    Return only the HIPAA safeguards that are partially satisfied or have gaps,
    along with the specific CMMC controls that need to be implemented.
    """
    assessments_map = await get_latest_assessments(db)
    results = [_assess_hipaa_control(h, assessments_map) for h in HIPAA_TO_CMMC]
    gaps = [r for r in results if r["hipaa_status"] != "satisfied"]

    return {
        "framework": "HIPAA Security Rule",
        "assessed_at": datetime.now(UTC).isoformat(),
        "total_gaps": len(gaps),
        "gaps": gaps,
    }


@router.get(
    "/mapping",
    summary="Full HIPAA → CMMC control cross-reference table",
)
async def get_hipaa_cmmc_mapping():
    """
    Return the complete static mapping of HIPAA safeguards to CMMC controls,
    without live assessment status. Useful for planning and documentation.
    """
    return {
        "framework": "HIPAA Security Rule (45 CFR Part 164)",
        "cmmc_framework": "CMMC 2.0 Level 2 / NIST SP 800-171",
        "total_safeguards": len(HIPAA_TO_CMMC),
        "safeguard_categories": ["Administrative", "Physical", "Technical", "Organizational", "Documentation"],
        "mapping": [
            {
                "hipaa_id": h["hipaa_id"],
                "cfr_section": h["cfr_section"],
                "safeguard_category": h["safeguard_category"],
                "title": h["title"],
                "required": h["required"],
                "cmmc_controls": h["cmmc_controls"],
                "cmmc_coverage_weight": h["cmmc_weight"],
                "gap_notes": h["gap_notes"],
            }
            for h in HIPAA_TO_CMMC
        ],
    }


@router.get(
    "/safeguard/{hipaa_id:path}",
    summary="Get HIPAA safeguard detail with current CMMC implementation status",
)
async def get_hipaa_safeguard_detail(
    hipaa_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return full detail for a specific HIPAA safeguard (e.g., 164.308(a)(1))
    including live CMMC control implementation status.
    """
    from fastapi import HTTPException

    safeguard = next(
        (h for h in HIPAA_TO_CMMC if h["hipaa_id"] == hipaa_id), None
    )
    if not safeguard:
        raise HTTPException(
            status_code=404,
            detail=f"HIPAA safeguard '{hipaa_id}' not found. "
                   f"Available: {[h['hipaa_id'] for h in HIPAA_TO_CMMC]}",
        )

    assessments_map = await get_latest_assessments(
        db, control_ids=safeguard["cmmc_controls"]
    )

    control_details = []
    for cid in safeguard["cmmc_controls"]:
        rec = assessments_map.get(cid)
        control_details.append(
            {
                "control_id": cid,
                "status": rec.status if rec else "not_started",
                "confidence": rec.confidence if rec else 0.0,
            }
        )

    result = _assess_hipaa_control(safeguard, assessments_map)
    result["cmmc_control_details"] = control_details
    return result
