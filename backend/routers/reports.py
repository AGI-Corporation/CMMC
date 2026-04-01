"""
SSP and POAM Report Generation Router
AGI Corporation 2026

Generates System Security Plans (SSP) and Plans of Action & Milestones (POA&M)
from the current assessment state. Output formats: Markdown, JSON, CSV.
Also exports NIST OSCAL (Open Security Controls Assessment Language) JSON for
C3PAO submissions.
"""

import csv
import io
import json
import uuid
from datetime import UTC, date, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (AssessmentRecord, ControlRecord,
                                 EvidenceRecord, get_db,
                                 get_latest_assessments)

router = APIRouter()


def get_status_emoji(status: str) -> str:
    """Map implementation status to a visual emoji for better scannability."""
    mapping = {
        "implemented": "✅",
        "partial": "🟡",
        "partially_implemented": "🟡",
        "planned": "📝",
        "not_implemented": "🛑",
        "na": "⚪",
        "not_started": "⚪",
    }
    return mapping.get(status, "⚪")


def get_progress_bar(percentage: float, width: int = 10) -> str:
    """Generate a markdown-compatible progress bar."""
    filled = int(round(percentage / 100 * width))
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar}` {percentage:.1f}%"


def get_confidence_stars(confidence: float) -> str:
    """Convert confidence float (0-1) to star rating (1-5), padded to 5 chars."""
    stars = int(confidence * 5 + 0.5)
    stars = max(1, min(5, stars))
    return "⭐" * stars + "☆" * (5 - stars)


@router.get("/ssp", summary="Generate System Security Plan (SSP) in Markdown")
async def generate_ssp(
    system_name: str = "AGI Corp CMMC System",
    classification: str = "CUI",
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a NIST SP 800-171 / CMMC 2.0 SSP in Markdown format.
    Includes: system overview, control family summaries, implementation status.
    """
    # Fetch latest assessments
    assessments_dict = await get_latest_assessments(db)
    assessments = list(assessments_dict.values())
    controls_result = await db.execute(select(ControlRecord))
    controls = {c.id: c for c in controls_result.scalars().all()}

    # Count by status
    status_counts = {
        "implemented": 0,
        "partial": 0,
        "planned": 0,
        "not_implemented": 0,
        "na": 0,
    }
    for a in assessments:
        if a.status in status_counts:
            status_counts[a.status] += 1
        elif a.status == "partially_implemented":
            status_counts["partial"] += 1

    total_controls = len(controls)
    implemented_pct = (
        (status_counts["implemented"] / total_controls * 100)
        if total_controls > 0
        else 0
    )

    sprs_estimate = 110 - (
        status_counts["not_implemented"] * 1 + status_counts["partial"] * 0.5
    )
    sprs_estimate = max(-203, round(sprs_estimate, 0))

    total_controls_count = len(controls)
    compliance_pct = (
        (status_counts["implemented"] / total_controls_count * 100)
        if total_controls_count > 0
        else 0
    )
    progress_bar = get_progress_bar(compliance_pct)

    ssp = f"""# System Security Plan (SSP)
## {system_name}

**Classification:** {classification}  
**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}
**Framework:** CMMC 2.0 Level 2 / NIST SP 800-171 Rev 2  
**SPRS Score Estimate:** {sprs_estimate}  
**Overall Compliance:** {get_progress_bar(implemented_pct)}

---

### Table of Contents
- [1. System Overview](#1-system-overview)
- [2. Control Implementation Summary](#2-control-implementation-summary)
- [3. Assessment Findings](#3-assessment-findings)
- [4. Next Steps](#4-next-steps)

---

## 1. System Overview

| Field | Value |
|-------|-------|
| System Name | {system_name} |
| Owner | AGI Corporation |
| Classification | {classification} |
| Assessment Date | {date.today()} |
| Total Controls | {total_controls} |
| Implemented | {get_status_emoji('implemented')} {status_counts['implemented']} |
| Partial | {get_status_emoji('partial')} {status_counts['partial']} |
| Planned | {get_status_emoji('planned')} {status_counts['planned']} |
| Not Implemented | {get_status_emoji('not_implemented')} {status_counts['not_implemented']} |
| N/A | {get_status_emoji('na')} {status_counts['na']} |

## 2. Control Implementation Summary

### Zero Trust Pillar Alignment

| ZT Pillar | CMMC Domains | Status |
|-----------|--------------|--------|
| User | AC, IA, PS | See assessment |
| Device | CM, MA, PE | See assessment |
| Network | SC, AC | See assessment |
| Application | CM, CA, SI | See assessment |
| Data | MP, SC, AU | See assessment |
| Visibility & Analytics | AU, IR, RA | See assessment |
| Automation & Orchestration | IR, SI, CA | See assessment |

## 3. Assessment Findings

*Note: Only the first 20 assessment findings are displayed in this summary.*

"""

    for a in assessments[:20]:  # Limit for readability
        ctrl = controls.get(a.control_id)
        ctrl_title = ctrl.title if ctrl else "Unknown"
        status_display = (
            f"{get_status_emoji(a.status)} {a.status.replace('_', ' ').title()}"
        )
        confidence_display = (
            f"{get_confidence_stars(a.confidence)} ({a.confidence:.0%})"
        )
        ssp += f"""### {a.control_id} - {ctrl_title}
- **Status:** {status_display}
- **Confidence:** {confidence_display}
- **Notes:** {a.notes or 'None'}
- **Evidence IDs:** {', '.join(a.evidence_ids or []) or 'None'}

"""

    ssp += """
## 4. Next Steps

1. Complete POA&M for all not_implemented controls
2. Collect evidence for partial controls
3. Schedule C3PAO assessment
4. Review and update SSP quarterly

---
*Generated by AGI Corporation CMMC Compliance Platform v1.0 | 🎨 Palette UX Enhanced*
"""
    return PlainTextResponse(content=ssp, media_type="text/markdown")


@router.get("/poam", summary="Generate POA&M CSV for unimplemented controls")
async def generate_poam(
    system_name: str = "AGI Corp CMMC System",
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a Plan of Action & Milestones (POA&M) as CSV.
    Includes all partial and not_implemented controls.
    """
    assessments_dict = await get_latest_assessments(db)
    assessments = list(assessments_dict.values())
    controls_result = await db.execute(select(ControlRecord))
    controls = {c.id: c for c in controls_result.scalars().all()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Control ID",
            "Domain",
            "Title",
            "ZT Pillar",
            "Status",
            "Confidence",
            "Milestone",
            "Target Date",
            "Responsible Party",
            "Resources Required",
            "Notes",
        ]
    )

    for a in assessments:
        if a.status in [
            "not_implemented",
            "partial",
            "planned",
            "partially_implemented",
        ]:
            ctrl = controls.get(a.control_id)
            domain = a.control_id.split(".")[0] if "." in a.control_id else ""
            writer.writerow(
                [
                    a.control_id,
                    domain,
                    ctrl.title if ctrl else "",
                    ctrl.zt_pillar if ctrl else "",
                    a.status,
                    f"{a.confidence:.0%}",
                    f"Implement {a.control_id}",
                    a.next_review.strftime("%Y-%m-%d") if a.next_review else "TBD",
                    a.assessor or "ISSO",
                    "TBD",
                    a.notes or "",
                ]
            )

    csv_content = output.getvalue()
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="poam_{system_name.replace(" ","_")}.csv"'
        },
    )


@router.get("/dashboard", summary="Get compliance dashboard summary")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """Return compliance posture summary for dashboard rendering."""
    assessments_dict = await get_latest_assessments(db)
    assessments = list(assessments_dict.values())

    status_counts = {
        "implemented": 0,
        "partial": 0,
        "planned": 0,
        "not_implemented": 0,
        "na": 0,
    }

    for a in assessments:
        if a.status in status_counts:
            status_counts[a.status] += 1
        elif a.status == "partially_implemented":
            status_counts["partial"] += 1

    total_assessed = len(assessments)
    implemented = status_counts["implemented"]
    sprs_score = max(
        -203,
        round(
            110 - (status_counts["not_implemented"] + status_counts["partial"] * 0.5)
        ),
    )

    # Get total controls count for accurate percentage
    controls_result = await db.execute(select(func.count(ControlRecord.id)))
    total_controls = controls_result.scalar_one()

    return {
        "system": "AGI Corp CMMC System",
        "generated_at": datetime.now(UTC).isoformat(),
        "sprs_score": sprs_score,
        "total_controls": total_controls,
        "assessed_controls": total_assessed,
        "status_breakdown": status_counts,
        "overall_compliance_pct": (
            round(implemented / total_controls * 100, 1) if total_controls else 0
        ),
        "zt_pillars": [
            {"pillar": "User", "domains": ["AC", "IA", "PS", "AT"]},
            {"pillar": "Device", "domains": ["CM", "MA", "PE"]},
            {"pillar": "Network", "domains": ["SC", "AC"]},
            {"pillar": "Application", "domains": ["CM", "CA", "SI"]},
            {"pillar": "Data", "domains": ["MP", "SC", "AU"]},
            {"pillar": "Visibility & Analytics", "domains": ["AU", "IR", "RA"]},
            {"pillar": "Automation & Orchestration", "domains": ["IR", "SI", "CA"]},
        ],
        "agents": [
            {"name": "orchestrator", "endpoint": "/api/orchestrator"},
            {"name": "icam", "endpoint": "/api/agents/icam"},
            {"name": "devsecops", "endpoint": "/api/agents/devsecops"},
            {"name": "mistral", "endpoint": "/api/agents/mistral"},
            {"name": "data_protection", "endpoint": "/api/agents/data"},
            {"name": "infrastructure", "endpoint": "/api/agents/infra"},
            {"name": "governance", "endpoint": "/api/agents/governance"},
            {"name": "operations", "endpoint": "/api/agents/ops"},
            {"name": "remediation", "endpoint": "/api/agents/remediation"},
            {"name": "supply_chain", "endpoint": "/api/agents/supply-chain"},
            {"name": "awareness", "endpoint": "/api/agents/awareness"},
        ],
    }


@router.get(
    "/oscal",
    summary="Export SSP as NIST OSCAL JSON (C3PAO-ready)",
)
async def export_oscal(
    system_name: str = "AGI Corp CMMC System",
    organization: str = "AGI Corporation",
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an NIST OSCAL (Open Security Controls Assessment Language) System
    Security Plan in JSON format, compatible with C3PAO assessment submissions
    and NIST OSCAL validation tooling.

    The export follows the OSCAL SSP schema (NIST SP 800-18 / NIST OSCAL 1.1).
    Includes system characteristics, implemented components, and control
    implementation statements derived from the current assessment state.
    """
    assessments_map = await get_latest_assessments(db)
    controls_result = await db.execute(select(ControlRecord))
    controls = {c.id: c for c in controls_result.scalars().all()}

    system_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    # ── Implemented components (one logical component per ZT pillar) ───────────
    components = [
        {
            "uuid": str(uuid.uuid4()),
            "type": "software",
            "title": f"{pillar} Controls Implementation",
            "description": f"Implementation component for CMMC controls under the {pillar} ZT pillar.",
            "status": {"state": "operational"},
        }
        for pillar in [
            "User", "Device", "Network", "Application",
            "Data", "Visibility & Analytics", "Automation & Orchestration",
        ]
    ]

    # ── Control implementation statements ─────────────────────────────────────
    implemented_requirements = []
    for ctrl_id, ctrl in controls.items():
        assessment = assessments_map.get(ctrl_id)
        status = assessment.status if assessment else "not_started"
        confidence = assessment.confidence if assessment else 0.0
        notes = assessment.notes if assessment else ""

        oscal_status_map = {
            "implemented": "implemented",
            "partially_implemented": "partially-implemented",
            "partial": "partially-implemented",
            "planned": "planned",
            "not_implemented": "not-implemented",
            "not_started": "not-implemented",
            "na": "not-applicable",
        }

        implemented_requirements.append(
            {
                "uuid": str(uuid.uuid4()),
                "control-id": ctrl_id.lower().replace(".", "-"),
                "description": ctrl.description or "",
                "statements": [
                    {
                        "statement-id": f"{ctrl_id.lower().replace('.', '-')}_smt",
                        "uuid": str(uuid.uuid4()),
                        "description": notes or f"Control {ctrl_id} implementation statement.",
                        "by-components": [
                            {
                                "component-uuid": components[0]["uuid"],
                                "uuid": str(uuid.uuid4()),
                                "description": notes or f"Implementation of {ctrl_id}.",
                                "implementation-status": {
                                    "state": oscal_status_map.get(status, "not-implemented"),
                                },
                                "remarks": f"Confidence: {confidence:.0%}. ZT Pillar: {ctrl.zt_pillar or 'N/A'}.",
                            }
                        ],
                    }
                ],
            }
        )

    oscal_ssp = {
        "system-security-plan": {
            "uuid": system_id,
            "metadata": {
                "title": f"{system_name} — CMMC 2.0 Level 2 System Security Plan",
                "last-modified": now_iso,
                "version": "1.0",
                "oscal-version": "1.1.2",
                "published": now_iso,
                "roles": [
                    {"id": "prepared-by", "title": "Prepared by"},
                    {"id": "prepared-for", "title": "Prepared for"},
                    {"id": "content-approver", "title": "Content Approver"},
                    {"id": "isso", "title": "Information System Security Officer"},
                ],
                "parties": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "type": "organization",
                        "name": organization,
                        "remarks": "Organization responsible for system security.",
                    }
                ],
            },
            "import-profile": {
                "href": "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-171/rev2/json/NIST_SP-800-171_rev2_profile.json",
                "remarks": "NIST SP 800-171 Rev 2 control profile (CMMC 2.0 Level 2 baseline).",
            },
            "system-characteristics": {
                "system-ids": [{"id": system_id, "identifier-type": "https://ietf.org/rfc/rfc4122"}],
                "system-name": system_name,
                "description": (
                    f"{system_name} processes Controlled Unclassified Information (CUI) "
                    "in support of DoD contracts and is subject to CMMC 2.0 Level 2 requirements."
                ),
                "security-sensitivity-level": "moderate",
                "system-information": {
                    "information-types": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "title": "Controlled Unclassified Information (CUI)",
                            "description": "CUI as defined by EO 13556 and 32 CFR Part 2002.",
                            "categorizations": [
                                {
                                    "system": "https://doi.org/10.6028/NIST.SP.800-60v2r1",
                                    "information-type-ids": ["C.2.8.12"],
                                }
                            ],
                            "confidentiality-impact": {"base": "moderate", "selected": "moderate"},
                            "integrity-impact": {"base": "moderate", "selected": "moderate"},
                            "availability-impact": {"base": "moderate", "selected": "low"},
                        }
                    ]
                },
                "security-impact-level": {
                    "security-objective-confidentiality": "moderate",
                    "security-objective-integrity": "moderate",
                    "security-objective-availability": "low",
                },
                "status": {"state": "operational"},
                "authorization-boundary": {
                    "description": (
                        "The authorization boundary encompasses all information systems, "
                        "components, and services that process, store, or transmit CUI."
                    )
                },
                "remarks": f"Generated by AGI Corporation CMMC Compliance Platform on {now_iso}",
            },
            "system-implementation": {
                "users": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": "Privileged Users",
                        "description": "System administrators and privileged accounts with elevated access.",
                        "role-ids": ["isso"],
                    },
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": "General Users",
                        "description": "Non-privileged users with standard access to CUI systems.",
                    },
                ],
                "components": components,
                "inventory-items": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "description": "Primary application server hosting CMMC platform.",
                        "implemented-components": [{"component-uuid": components[0]["uuid"]}],
                        "props": [
                            {"name": "asset-type", "value": "os"},
                            {"name": "is-scanned", "value": "yes"},
                        ],
                    }
                ],
            },
            "control-implementation": {
                "description": (
                    "This section documents the implementation status of each CMMC 2.0 "
                    "Level 2 control (NIST SP 800-171 Rev 2) for this system."
                ),
                "implemented-requirements": implemented_requirements,
            },
            "back-matter": {
                "resources": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": "NIST SP 800-171 Rev 2",
                        "rlinks": [
                            {"href": "https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final"}
                        ],
                    },
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": "CMMC 2.0 Level 2 Assessment Guide",
                        "rlinks": [
                            {"href": "https://www.acq.osd.mil/cmmc/"}
                        ],
                    },
                ]
            },
        }
    }

    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=oscal_ssp,
        headers={
            "Content-Disposition": f'attachment; filename="oscal_ssp_{system_name.replace(" ", "_")}.json"',
            "Content-Type": "application/json",
        },
    )


@router.get(
    "/maturity-heatmap",
    summary="ZT pillar × CMMC domain compliance maturity cross-matrix",
    description=(
        "Return a two-dimensional compliance maturity matrix mapping each DoD Zero Trust "
        "pillar against the CMMC domains it governs. Each cell reports the number of "
        "implemented vs total controls, average confidence, and an overall maturity score "
        "(0.0–1.0). Useful for identifying which pillar–domain intersections need the most "
        "attention. Maps to CA.2.157 (continuous monitoring) and RA.2.141 (risk assessment)."
    ),
)
async def get_maturity_heatmap(
    db: AsyncSession = Depends(get_db),
):
    """Return a ZT pillar × CMMC domain maturity cross-matrix."""
    ZT_DOMAIN_MAP = {
        "User": ["AC", "IA", "PS", "AT"],
        "Device": ["CM", "MA", "PE"],
        "Network": ["SC", "AC"],
        "Application": ["CM", "CA", "SI"],
        "Data": ["MP", "SC", "AU"],
        "Visibility & Analytics": ["AU", "IR", "RA"],
        "Automation & Orchestration": ["IR", "SI", "CA", "SR"],
    }

    # Load controls and latest assessments
    ctrl_result = await db.execute(select(ControlRecord))
    controls = {c.id: c for c in ctrl_result.scalars().all()}
    assessments_map = await get_latest_assessments(db)

    # Build domain-level stats
    domain_stats: Dict[str, Dict] = {}
    for ctrl_id, ctrl in controls.items():
        d = ctrl.domain
        if d not in domain_stats:
            domain_stats[d] = {"total": 0, "implemented": 0, "confidence_sum": 0.0, "assessed": 0}
        domain_stats[d]["total"] += 1
        assessment = assessments_map.get(ctrl_id)
        if assessment:
            domain_stats[d]["assessed"] += 1
            domain_stats[d]["confidence_sum"] += assessment.confidence
            if assessment.status == "implemented":
                domain_stats[d]["implemented"] += 1

    def _cell(pillar: str, domain: str) -> Dict[str, Any]:
        ds = domain_stats.get(domain, {"total": 0, "implemented": 0, "confidence_sum": 0.0, "assessed": 0})
        total = ds["total"]
        implemented = ds["implemented"]
        assessed = ds["assessed"]
        avg_confidence = round(ds["confidence_sum"] / assessed, 3) if assessed else 0.0
        maturity = round(implemented / total, 3) if total else 0.0
        return {
            "pillar": pillar,
            "domain": domain,
            "total_controls": total,
            "implemented": implemented,
            "avg_confidence": avg_confidence,
            "maturity_score": maturity,
        }

    # Build matrix
    matrix = []
    all_domains_seen = set()
    for pillar, domains in ZT_DOMAIN_MAP.items():
        for domain in domains:
            if domain not in all_domains_seen:
                all_domains_seen.add(domain)
            matrix.append(_cell(pillar, domain))

    # Pillar-level rollup
    pillar_rollup = []
    for pillar, domains in ZT_DOMAIN_MAP.items():
        cells = [c for c in matrix if c["pillar"] == pillar]
        total = sum(c["total_controls"] for c in cells)
        implemented = sum(c["implemented"] for c in cells)
        avg_confidence = round(
            sum(c["avg_confidence"] for c in cells) / len(cells), 3
        ) if cells else 0.0
        maturity = round(implemented / total, 3) if total else 0.0
        pillar_rollup.append({
            "pillar": pillar,
            "domains": domains,
            "total_controls": total,
            "implemented": implemented,
            "avg_confidence": avg_confidence,
            "maturity_score": maturity,
        })

    # Sort pillars by maturity_score ascending (lowest-maturity first for prioritisation)
    pillar_rollup.sort(key=lambda r: r["maturity_score"])

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "pillar_rollup": pillar_rollup,
        "matrix": matrix,
    }
