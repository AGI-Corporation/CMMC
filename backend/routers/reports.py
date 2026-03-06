"""
SSP and POAM Report Generation Router
AGI Corporation 2026

Generates System Security Plans (SSP) and Plans of Action & Milestones (POA&M)
from the current assessment state. Output formats: Markdown, JSON, CSV.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, date, UTC
import csv
import io

from backend.db.database import get_db, AssessmentRecord, ControlRecord

router = APIRouter()

DOMAIN_NAMES = {
    "AC": "Access Control",
    "AU": "Audit and Accountability",
    "CM": "Configuration Management",
    "IA": "Identification and Authentication",
    "IR": "Incident Response",
    "MA": "Maintenance",
    "MP": "Media Protection",
    "PS": "Personnel Security",
    "PE": "Physical Protection",
    "RA": "Risk Assessment",
    "CA": "Security Assessment",
    "SA": "Situational Awareness",
    "SC": "System and Communications Protection",
    "SI": "System and Information Integrity",
}


def get_status_visual(status: str) -> str:
    """Returns an emoji and label for the status."""
    mapping = {
        "implemented": "✅ Implemented",
        "partial": "🟡 Partial",
        "partially_implemented": "🟡 Partial",
        "planned": "📅 Planned",
        "not_implemented": "❌ Not Implemented",
        "na": "⚪ N/A",
    }
    return mapping.get(status, f"❓ {status}")


def get_confidence_stars(confidence: float) -> str:
    """Returns a star rating for confidence."""
    stars = int(round(confidence * 5))
    return "⭐" * stars + "☆" * (5 - stars)


async def get_latest_assessments(db: AsyncSession):
    # Subquery for latest assessment date per control_id
    subquery = (
        select(
            AssessmentRecord.control_id,
            func.max(AssessmentRecord.assessment_date).label("max_date"),
        )
        .group_by(AssessmentRecord.control_id)
        .subquery()
    )

    # Join with the original table to get full records
    query = select(AssessmentRecord).join(
        subquery,
        (AssessmentRecord.control_id == subquery.c.control_id)
        & (AssessmentRecord.assessment_date == subquery.c.max_date),
    )

    result = await db.execute(query)
    return result.scalars().all()


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
    assessments = await get_latest_assessments(db)
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

    sprs_estimate = 110 - (
        status_counts["not_implemented"] * 1 + status_counts["partial"] * 0.5
    )
    sprs_estimate = max(-203, round(sprs_estimate, 0))

    total_controls_count = len(controls)
    implemented_count = status_counts["implemented"]
    pct = (
        (implemented_count / total_controls_count * 100)
        if total_controls_count > 0
        else 0
    )

    if pct >= 100:
        readiness_label = "🏆 Ready for Certification"
    elif pct >= 80:
        readiness_label = "🟢 Near Compliant - Minor Gaps"
    elif pct >= 60:
        readiness_label = "🟡 In Progress - Significant Gaps"
    else:
        readiness_label = "⚠️ Early Stage - Major Remediation Needed"

    # Calculate ZT Pillar Stats
    zt_mapping = {
        "User": ["AC", "IA", "PS"],
        "Device": ["CM", "MA", "PE"],
        "Network": ["SC", "AC"],
        "Application": ["CM", "CA", "SI"],
        "Data": ["MP", "SC", "AU"],
        "Visibility & Analytics": ["AU", "IR", "RA"],
        "Automation & Orchestration": ["IR", "SI", "CA"],
    }
    zt_stats = {p: {"total": 0, "implemented": 0} for p in zt_mapping}

    for cid, ctrl in controls.items():
        domain = ctrl.domain
        assessment = next((a for a in assessments if a.control_id == cid), None)
        is_implemented = assessment and assessment.status == "implemented"
        for pillar, domains in zt_mapping.items():
            if domain in domains:
                zt_stats[pillar]["total"] += 1
                if is_implemented:
                    zt_stats[pillar]["implemented"] += 1

    ssp = f"""# System Security Plan (SSP)
## {system_name}

**Classification:** {classification}
**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}
**Framework:** CMMC 2.0 Level 2 / NIST SP 800-171 Rev 2  
**Overall Readiness:** {readiness_label}
**SPRS Score Estimate:** {sprs_estimate}  

---

## 1. System Overview

| Field | Value |
|-------|-------|
| System Name | {system_name} |
| Owner | AGI Corporation |
| Classification | {classification} |
| Assessment Date | {date.today()} |
| Total Controls | {len(controls)} |
| Implemented | {status_counts['implemented']} |
| Partial | {status_counts['partial']} |
| Planned | {status_counts['planned']} |
| Not Implemented | {status_counts['not_implemented']} |
| N/A | {status_counts['na']} |

## 2. Control Implementation Summary

### Zero Trust Pillar Alignment

| ZT Pillar | CMMC Domains | Implementation | Status |
|-----------|--------------|----------------|--------|
| User | AC, IA, PS | {zt_stats['User']['implemented']}/{zt_stats['User']['total']} | {"✅" if zt_stats['User']['implemented'] == zt_stats['User']['total'] and zt_stats['User']['total'] > 0 else "🟡"} |
| Device | CM, MA, PE | {zt_stats['Device']['implemented']}/{zt_stats['Device']['total']} | {"✅" if zt_stats['Device']['implemented'] == zt_stats['Device']['total'] and zt_stats['Device']['total'] > 0 else "🟡"} |
| Network | SC, AC | {zt_stats['Network']['implemented']}/{zt_stats['Network']['total']} | {"✅" if zt_stats['Network']['implemented'] == zt_stats['Network']['total'] and zt_stats['Network']['total'] > 0 else "🟡"} |
| Application | CM, CA, SI | {zt_stats['Application']['implemented']}/{zt_stats['Application']['total']} | {"✅" if zt_stats['Application']['implemented'] == zt_stats['Application']['total'] and zt_stats['Application']['total'] > 0 else "🟡"} |
| Data | MP, SC, AU | {zt_stats['Data']['implemented']}/{zt_stats['Data']['total']} | {"✅" if zt_stats['Data']['implemented'] == zt_stats['Data']['total'] and zt_stats['Data']['total'] > 0 else "🟡"} |
| Visibility & Analytics | AU, IR, RA | {zt_stats['Visibility & Analytics']['implemented']}/{zt_stats['Visibility & Analytics']['total']} | {"✅" if zt_stats['Visibility & Analytics']['implemented'] == zt_stats['Visibility & Analytics']['total'] and zt_stats['Visibility & Analytics']['total'] > 0 else "🟡"} |
| Automation & Orchestration | IR, SI, CA | {zt_stats['Automation & Orchestration']['implemented']}/{zt_stats['Automation & Orchestration']['total']} | {"✅" if zt_stats['Automation & Orchestration']['implemented'] == zt_stats['Automation & Orchestration']['total'] and zt_stats['Automation & Orchestration']['total'] > 0 else "🟡"} |

## 3. Assessment Findings

"""

    # Group findings by domain
    findings_by_domain = {}
    for a in assessments:
        ctrl = controls.get(a.control_id)
        if not ctrl:
            continue
        domain = ctrl.domain
        if domain not in findings_by_domain:
            findings_by_domain[domain] = []
        findings_by_domain[domain].append(a)

    # Sort domains alphabetically
    sorted_domains = sorted(findings_by_domain.keys())

    for domain_code in sorted_domains:
        domain_name = DOMAIN_NAMES.get(domain_code, domain_code)
        ssp += f"### {domain_code} - {domain_name}\n\n"

        # Sort assessments by control ID
        domain_assessments = sorted(
            findings_by_domain[domain_code], key=lambda x: x.control_id
        )

        for a in domain_assessments:
            ctrl = controls.get(a.control_id)
            ctrl_title = ctrl.title if ctrl else "Unknown"
            status_visual = get_status_visual(a.status)
            confidence_visual = get_confidence_stars(a.confidence)

            ssp += f"#### {a.control_id} - {ctrl_title}\n"
            ssp += f"- **Status:** {status_visual}\n"
            ssp += f"- **Confidence:** {confidence_visual} ({a.confidence:.0%})\n"
            ssp += f"- **Notes:** {a.notes or 'None'}\n"
            ssp += (
                f"- **Evidence IDs:** {', '.join(a.evidence_ids or []) or 'None'}\n\n"
            )

    ssp += """
## 4. Next Steps

1. Complete POA&M for all not_implemented controls
2. Collect evidence for partial controls
3. Schedule C3PAO assessment
4. Review and update SSP quarterly

---
*Generated by AGI Corporation CMMC Compliance Platform v1.0 | Mistral AI-powered*
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
    assessments = await get_latest_assessments(db)
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
    assessments = await get_latest_assessments(db)

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
            {"pillar": "User", "domains": ["AC", "IA", "PS"]},
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
        ],
    }
