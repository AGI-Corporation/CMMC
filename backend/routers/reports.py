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
from typing import List, Dict, Any
from datetime import datetime, date, UTC
import csv
import io
import json

from backend.db.database import get_db, AssessmentRecord, ControlRecord, EvidenceRecord

router = APIRouter()

def get_status_emoji(status: str) -> str:
    """Map implementation status to visual emojis."""
    mapping = {
        "implemented": "✅",
        "partial": "🟡",
        "partially_implemented": "🟡",
        "planned": "📝",
        "not_implemented": "🛑",
        "na": "⚪",
        "not_started": "⚪"
    }
    return mapping.get(status, "⚪")

def get_confidence_stars(confidence: float) -> str:
    """Convert confidence float (0.0-1.0) to star rating."""
    # Use standard rounding (0.5 rounds up)
    stars = int(confidence * 5 + 0.5)
    return "⭐" * stars if stars > 0 else "🌑"

def get_progress_bar(percentage: float, length: int = 20) -> str:
    """Generate a Markdown-compatible progress bar."""
    filled = max(0, min(length, round((percentage / 100) * length)))
    bar = "█" * filled + "░" * (length - filled)
    return f"`{bar}` {percentage:.1f}%"

async def get_latest_assessments(db: AsyncSession):
    # Subquery for latest assessment date per control_id
    subquery = (
        select(
            AssessmentRecord.control_id,
            func.max(AssessmentRecord.assessment_date).label("max_date")
        )
        .group_by(AssessmentRecord.control_id)
        .subquery()
    )

    # Join with the original table to get full records
    query = (
        select(AssessmentRecord)
        .join(
            subquery,
            (AssessmentRecord.control_id == subquery.c.control_id) &
            (AssessmentRecord.assessment_date == subquery.c.max_date)
        )
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
    status_counts = {"implemented": 0, "partial": 0, "planned": 0, "not_implemented": 0, "na": 0}
    for a in assessments:
        if a.status in status_counts:
            status_counts[a.status] += 1
        elif a.status == "partially_implemented":
             status_counts["partial"] += 1

    sprs_estimate = 110 - (status_counts["not_implemented"] * 1 + status_counts["partial"] * 0.5)
    sprs_estimate = max(-203, round(sprs_estimate, 0))

    total_controls = len(controls)
    implemented_count = status_counts['implemented']
    compliance_pct = (implemented_count / total_controls * 100) if total_controls > 0 else 0

    ssp = f"""# System Security Plan (SSP)
## {system_name}

**Classification:** {classification}  
**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}
**Framework:** CMMC 2.0 Level 2 / NIST SP 800-171 Rev 2  
**Overall Compliance:** {get_progress_bar(compliance_pct)}
**SPRS Score Estimate:** {sprs_estimate}  

---

## 1. System Overview

| Field | Value |
|-------|-------|
| System Name | {system_name} |
| Owner | AGI Corporation |
| Classification | {classification} |
| Assessment Date | {date.today()} |
| Total Controls | {total_controls} |
| {get_status_emoji('implemented')} Implemented | {status_counts['implemented']} |
| {get_status_emoji('partial')} Partial | {status_counts['partial']} |
| {get_status_emoji('planned')} Planned | {status_counts['planned']} |
| {get_status_emoji('not_implemented')} Not Implemented | {status_counts['not_implemented']} |
| {get_status_emoji('na')} N/A | {status_counts['na']} |

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

"""

    for a in assessments[:20]:  # Limit for readability
        ctrl = controls.get(a.control_id)
        ctrl_title = ctrl.title if ctrl else "Unknown"
        ssp += f"""### {a.control_id} - {ctrl_title}
- **Status:** {get_status_emoji(a.status)} {a.status}
- **Confidence:** {get_confidence_stars(a.confidence)} ({a.confidence:.0%})
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
    writer.writerow([
        "Control ID", "Domain", "Title", "ZT Pillar", "Status",
        "Confidence", "Milestone", "Target Date", "Responsible Party",
        "Resources Required", "Notes"
    ])

    for a in assessments:
        if a.status in ["not_implemented", "partial", "planned", "partially_implemented"]:
            ctrl = controls.get(a.control_id)
            domain = a.control_id.split(".")[0] if "." in a.control_id else ""
            writer.writerow([
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
            ])

    csv_content = output.getvalue()
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="poam_{system_name.replace(" ","_")}.csv"'},
    )


@router.get("/dashboard", summary="Get compliance dashboard summary")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """Return compliance posture summary for dashboard rendering."""
    assessments = await get_latest_assessments(db)

    status_counts = {"implemented": 0, "partial": 0, "planned": 0, "not_implemented": 0, "na": 0}

    for a in assessments:
        if a.status in status_counts:
            status_counts[a.status] += 1
        elif a.status == "partially_implemented":
             status_counts["partial"] += 1

    total_assessed = len(assessments)
    implemented = status_counts["implemented"]
    sprs_score = max(-203, round(110 - (status_counts["not_implemented"] + status_counts["partial"] * 0.5)))

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
        "overall_compliance_pct": round(implemented / total_controls * 100, 1) if total_controls else 0,
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
