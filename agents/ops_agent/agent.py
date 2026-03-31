"""
Operations Agent - ZT Automation & Orchestration Pillar
AGI Corporation 2026

Aligns with CMMC Incident Response (IR) and Audit & Accountability (AU)
domains. Fulcrum LOE 3 - Security operations and incident management.

Responsibilities: incident response readiness, SIEM coverage verification,
audit trail integrity, tabletop exercise tracking, alert triage simulation.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

OPS_CONTROLS = [
    "IR.2.092",
    "IR.2.093",
    "IR.2.094",
    "IR.2.096",
    "IR.2.097",
    "IR.3.098",
    "AU.2.041",
    "AU.2.042",
    "AU.2.043",
    "AU.2.044",
    "AU.3.045",
    "AU.3.046",
]


class IncidentSeverity(str, Enum):
    P1 = "P1"  # Critical — active breach
    P2 = "P2"  # High — significant impact
    P3 = "P3"  # Medium — limited impact
    P4 = "P4"  # Low — informational


class IncidentState(str, Enum):
    OPEN = "open"
    TRIAGED = "triaged"
    CONTAINED = "contained"
    ERADICATED = "eradicated"
    RECOVERED = "recovered"
    CLOSED = "closed"


@dataclass
class SIEMSource:
    source_id: str
    name: str
    log_type: str  # endpoint / network / cloud / application / identity
    enabled: bool
    ingestion_lag_mins: int
    alert_rules: int
    tuned: bool


@dataclass
class IncidentRecord:
    incident_id: str
    title: str
    severity: IncidentSeverity
    state: IncidentState
    detected_at: datetime
    reported_at: Optional[datetime]
    contained_at: Optional[datetime]
    time_to_detect_mins: int
    time_to_report_mins: Optional[int]
    time_to_contain_mins: Optional[int]
    affected_controls: List[str]
    lessons_learned: bool


@dataclass
class TabletopExercise:
    exercise_id: str
    scenario: str
    conducted_at: Optional[datetime]
    participants: List[str]
    passed: bool
    gaps_identified: List[str]


@dataclass
class OpsAssessmentResult:
    control_id: str
    status: str
    confidence: float
    findings: List[str]
    evidence_id: str
    remediation: List[str]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class OperationsAgent:
    """
    Operations Agent aligned to ZT Automation & Orchestration Pillar.
    """

    # DoD reporting timelines (in minutes)
    IR_REPORT_THRESHOLD_MINS = 60  # Report within 1 hour
    IR_CONTAIN_THRESHOLD_HOURS = 24  # Contain within 24 hours
    AUDIT_RETENTION_DAYS = 90  # Minimum online retention

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.siem_sources: List[SIEMSource] = []
        self.incidents: List[IncidentRecord] = []
        self.tabletop_exercises: List[TabletopExercise] = []
        if mock_mode:
            self._load_mock_ops_data()

    def _load_mock_ops_data(self):
        now = datetime.now(UTC)

        self.siem_sources = [
            SIEMSource(
                source_id="siem001",
                name="Endpoint EDR Feed",
                log_type="endpoint",
                enabled=True,
                ingestion_lag_mins=2,
                alert_rules=147,
                tuned=True,
            ),
            SIEMSource(
                source_id="siem002",
                name="Network Flow Logs",
                log_type="network",
                enabled=True,
                ingestion_lag_mins=5,
                alert_rules=62,
                tuned=False,
            ),
            SIEMSource(
                source_id="siem003",
                name="Cloud Audit Trail (AWS/GCP)",
                log_type="cloud",
                enabled=True,
                ingestion_lag_mins=10,
                alert_rules=38,
                tuned=True,
            ),
            SIEMSource(
                source_id="siem004",
                name="Identity Provider Logs",
                log_type="identity",
                enabled=False,
                ingestion_lag_mins=0,
                alert_rules=0,
                tuned=False,
            ),
            SIEMSource(
                source_id="siem005",
                name="Application Error Logs",
                log_type="application",
                enabled=True,
                ingestion_lag_mins=15,
                alert_rules=22,
                tuned=False,
            ),
        ]

        self.incidents = [
            IncidentRecord(
                incident_id="inc001",
                title="Credential Stuffing Attempt — User Portal",
                severity=IncidentSeverity.P2,
                state=IncidentState.CLOSED,
                detected_at=now - timedelta(days=20),
                reported_at=now - timedelta(days=20, minutes=-45),
                contained_at=now - timedelta(days=19),
                time_to_detect_mins=12,
                time_to_report_mins=45,
                time_to_contain_mins=1430,
                affected_controls=["AC.2.006", "IA.3.083"],
                lessons_learned=True,
            ),
            IncidentRecord(
                incident_id="inc002",
                title="Unpatched Server Exploitation Attempt",
                severity=IncidentSeverity.P1,
                state=IncidentState.ERADICATED,
                detected_at=now - timedelta(days=5),
                reported_at=now - timedelta(days=5, minutes=-30),
                contained_at=now - timedelta(days=4),
                time_to_detect_mins=35,
                time_to_report_mins=30,
                time_to_contain_mins=720,
                affected_controls=["CM.3.068", "SI.1.210", "IR.2.092"],
                lessons_learned=False,
            ),
            IncidentRecord(
                incident_id="inc003",
                title="Unauthorized Privileged Access — Admin Panel",
                severity=IncidentSeverity.P2,
                state=IncidentState.OPEN,
                detected_at=now - timedelta(hours=2),
                reported_at=None,
                contained_at=None,
                time_to_detect_mins=8,
                time_to_report_mins=None,
                time_to_contain_mins=None,
                affected_controls=["AC.2.007", "IA.3.083", "AU.2.041"],
                lessons_learned=False,
            ),
        ]

        self.tabletop_exercises = [
            TabletopExercise(
                exercise_id="tt001",
                scenario="Ransomware Attack on CUI Repository",
                conducted_at=now - timedelta(days=180),
                participants=["CISO", "SOC Lead", "IT Manager", "Legal"],
                passed=True,
                gaps_identified=["No offline backups for CUI repo", "Slow notification chain"],
            ),
            TabletopExercise(
                exercise_id="tt002",
                scenario="Insider Threat — Data Exfiltration",
                conducted_at=None,
                participants=[],
                passed=False,
                gaps_identified=["Exercise not yet conducted"],
            ),
        ]

    def check_incident_response_plan(self) -> OpsAssessmentResult:
        """Assess IR.2.092 / IR.2.093 — Documented and tested IR capability."""
        ir_policy = next(
            (
                tt
                for tt in self.tabletop_exercises
                if tt.conducted_at is not None and tt.passed
            ),
            None,
        )
        conducted_exercises = [
            tt for tt in self.tabletop_exercises if tt.conducted_at is not None
        ]
        all_gaps = [
            g for tt in conducted_exercises for g in tt.gaps_identified
        ]
        missing_exercises = [
            tt for tt in self.tabletop_exercises if tt.conducted_at is None
        ]

        findings = []
        remediation = []

        if not conducted_exercises:
            findings.append("No IR tabletop exercises conducted")
            remediation.append(
                "Conduct annual IR tabletop exercise covering at least ransomware and data breach scenarios"
            )
        elif missing_exercises:
            names = [tt.scenario for tt in missing_exercises]
            findings.append(f"Planned exercises not yet conducted: {names}")
            remediation.append(
                "Schedule and conduct remaining IR tabletop exercises; document outcomes"
            )
        if all_gaps:
            findings.append(f"IR gaps identified in exercises: {all_gaps}")
            remediation.append(
                "Create POA&M entries for each exercise gap; resolve before next assessment"
            )

        confidence = 0.7 if ir_policy else 0.3
        if conducted_exercises and len(conducted_exercises) >= len(self.tabletop_exercises):
            confidence = min(confidence + 0.2, 1.0)

        status = (
            "implemented"
            if confidence >= 0.85
            else (
                "partially_implemented" if confidence >= 0.5 else "not_implemented"
            )
        )

        return OpsAssessmentResult(
            control_id="IR.2.092",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_incident_reporting_timelines(self) -> OpsAssessmentResult:
        """Assess IR.2.093 / IR.2.094 — DoD reporting timeline compliance."""
        closed = [i for i in self.incidents if i.state != IncidentState.OPEN]
        late_reports = [
            i
            for i in closed
            if i.time_to_report_mins is not None
            and i.time_to_report_mins > self.IR_REPORT_THRESHOLD_MINS
        ]
        open_unreported = [
            i
            for i in self.incidents
            if i.state == IncidentState.OPEN and i.reported_at is None
        ]
        lessons_missing = [
            i for i in closed if not i.lessons_learned
        ]

        findings = []
        remediation = []

        if late_reports:
            ids = [i.incident_id for i in late_reports]
            findings.append(
                f"Incidents reported beyond 1-hour DoD threshold: {ids}"
            )
            remediation.append(
                "Implement automated incident notification to AO/CCIO within 60 minutes of detection"
            )
        if open_unreported:
            ids = [i.incident_id for i in open_unreported]
            findings.append(
                f"Active incidents not yet reported to Authorizing Official: {ids}"
            )
            remediation.append(
                "Immediately report active incidents per DoD CIO 8500.01 requirements"
            )
        if lessons_missing:
            ids = [i.incident_id for i in lessons_missing]
            findings.append(
                f"Closed incidents without lessons-learned documentation: {ids}"
            )
            remediation.append(
                "Conduct post-incident reviews within 5 business days; document in IR tracker"
            )

        total = len(self.incidents)
        ok = total - len(late_reports) - len(open_unreported) - len(lessons_missing)
        confidence = max(0.0, ok / max(total, 1))

        status = (
            "implemented"
            if confidence >= 0.85
            else (
                "partially_implemented" if confidence >= 0.5 else "not_implemented"
            )
        )

        return OpsAssessmentResult(
            control_id="IR.2.093",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_siem_coverage(self) -> OpsAssessmentResult:
        """Assess AU.2.041 / AU.2.042 / AU.3.045 — SIEM and audit coverage."""
        enabled = [s for s in self.siem_sources if s.enabled]
        tuned = [s for s in enabled if s.tuned]
        high_lag = [s for s in enabled if s.ingestion_lag_mins > 30]

        findings = []
        remediation = []

        disabled = [s for s in self.siem_sources if not s.enabled]
        if disabled:
            names = [s.name for s in disabled]
            findings.append(f"Log sources not ingested by SIEM: {names}")
            remediation.append(
                "Onboard all log sources to SIEM; prioritize identity provider and privileged access logs"
            )
        if high_lag:
            names = [s.name for s in high_lag]
            findings.append(
                f"Log sources with >30 min ingestion lag (near-real-time required): {names}"
            )
            remediation.append(
                "Optimize log forwarding pipelines to achieve <5 minute ingestion lag for all sources"
            )
        untuned = [s for s in enabled if not s.tuned]
        if untuned:
            names = [s.name for s in untuned]
            findings.append(f"SIEM alert rules not tuned (high false-positive risk): {names}")
            remediation.append(
                "Tune detection rules using MITRE ATT&CK baseline; reduce false positives by ≥50%"
            )

        total = len(self.siem_sources)
        confidence = (
            0.5 * (len(enabled) / total)
            + 0.3 * (len(tuned) / total)
            + 0.2 * max(0, 1 - len(high_lag) / max(len(enabled), 1))
        ) if total else 0.0

        status = (
            "implemented"
            if confidence >= 0.85
            else (
                "partially_implemented" if confidence >= 0.5 else "not_implemented"
            )
        )

        return OpsAssessmentResult(
            control_id="AU.2.041",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def triage_incident(self, incident_type: str, description: str) -> Dict[str, Any]:
        """
        Simulate real-time incident triage workflow.
        Returns initial severity classification, notified parties, and
        immediate response actions mapped to CMMC IR controls.
        """
        # Simple keyword-based classification
        severity = IncidentSeverity.P3
        if any(k in description.lower() for k in ("ransomware", "breach", "exfil", "root")):
            severity = IncidentSeverity.P1
        elif any(k in description.lower() for k in ("credential", "privilege", "lateral")):
            severity = IncidentSeverity.P2
        elif any(k in description.lower() for k in ("phish", "malware", "scan")):
            severity = IncidentSeverity.P3

        actions = {
            IncidentSeverity.P1: [
                "Immediately isolate affected systems from network",
                "Notify CISO, AO, and DoD CIO within 1 hour",
                "Preserve forensic evidence before remediation",
                "Activate IR retainer / engage CISA if CUI exfiltrated",
            ],
            IncidentSeverity.P2: [
                "Quarantine affected accounts and endpoints",
                "Notify ISSO and system owner within 1 hour",
                "Begin forensic capture and timeline analysis",
                "Implement emergency access control restrictions",
            ],
            IncidentSeverity.P3: [
                "Document incident in IR tracking system",
                "Block associated IOCs at perimeter",
                "Monitor for escalation indicators",
                "Notify security team within 4 hours",
            ],
            IncidentSeverity.P4: [
                "Log and track in ticketing system",
                "Apply standard remediation procedure",
                "Update threat intel feeds",
            ],
        }

        cmmc_controls_engaged = {
            IncidentSeverity.P1: ["IR.2.092", "IR.2.093", "IR.2.094", "IR.3.098", "AU.2.041"],
            IncidentSeverity.P2: ["IR.2.092", "IR.2.093", "IR.2.094", "AU.2.041"],
            IncidentSeverity.P3: ["IR.2.092", "IR.2.093", "AU.2.041", "AU.2.042"],
            IncidentSeverity.P4: ["IR.2.092", "AU.2.041"],
        }

        return {
            "incident_id": str(uuid.uuid4()),
            "incident_type": incident_type,
            "description": description,
            "severity": severity,
            "classified_at": datetime.now(UTC).isoformat(),
            "cmmc_controls_engaged": cmmc_controls_engaged[severity],
            "zt_pillar": "Automation & Orchestration",
            "immediate_actions": actions[severity],
            "report_deadline": (
                (datetime.now(UTC) + timedelta(hours=1)).isoformat()
                if severity in (IncidentSeverity.P1, IncidentSeverity.P2)
                else None
            ),
        }

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all Operations assessments and return evidence-ready results."""
        assessments = [
            self.check_incident_response_plan(),
            self.check_incident_reporting_timelines(),
            self.check_siem_coverage(),
        ]

        zt_map = {
            "IR.2.092": "Automation & Orchestration",
            "IR.2.093": "Automation & Orchestration",
            "AU.2.041": "Visibility & Analytics",
        }

        results = []
        for a in assessments:
            results.append(
                {
                    "control_id": a.control_id,
                    "zt_pillar": zt_map.get(a.control_id, "Automation & Orchestration"),
                    "status": a.status,
                    "confidence": a.confidence,
                    "findings": a.findings,
                    "remediation": a.remediation,
                    "evidence_id": a.evidence_id,
                    "assessed_at": a.assessed_at.isoformat(),
                    "owner_agent": "operations",
                }
            )

        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="operations",
            trigger=trigger,
            scope="Automation & Orchestration Pillar",
            controls_evaluated=[a.control_id for a in assessments],
            findings={"results": results},
            status="completed",
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(record)
        await db.commit()
        return results


router = APIRouter()
_ops = OperationsAgent(mock_mode=True)


@router.get(
    "/assess",
    summary="Run full Operations assessment (ZT Automation & Orchestration Pillar)",
)
async def run_ops_assessment(db: AsyncSession = Depends(get_db)):
    """IR readiness, reporting timelines, SIEM coverage — ZT Automation Pillar."""
    results = await _ops.run_full_assessment(db)
    return {
        "agent": "operations",
        "zt_pillar": "Automation & Orchestration",
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/incident/triage",
    summary="Triage an incoming security incident and generate IR action plan",
)
async def triage_incident(
    incident_type: str = Body(..., embed=True),
    description: str = Body(..., embed=True),
):
    """
    Submit an incident for automated triage. Returns severity classification,
    CMMC IR controls engaged, and immediate response actions.
    """
    return _ops.triage_incident(incident_type, description)


@router.get("/siem-status", summary="Get SIEM source coverage and ingestion health")
async def get_siem_status():
    """Return SIEM log source inventory with coverage and tuning status."""
    total = len(_ops.siem_sources)
    enabled = sum(1 for s in _ops.siem_sources if s.enabled)
    return {
        "total_sources": total,
        "enabled_sources": enabled,
        "coverage_pct": round(enabled / total * 100, 1) if total else 0,
        "tuned_sources": sum(1 for s in _ops.siem_sources if s.tuned),
        "total_alert_rules": sum(s.alert_rules for s in _ops.siem_sources),
        "sources": [
            {
                "source_id": s.source_id,
                "name": s.name,
                "log_type": s.log_type,
                "enabled": s.enabled,
                "ingestion_lag_mins": s.ingestion_lag_mins,
                "alert_rules": s.alert_rules,
                "tuned": s.tuned,
            }
            for s in _ops.siem_sources
        ],
    }


@router.get("/incidents", summary="List recent security incidents with IR timeline metrics")
async def list_incidents():
    """Return incident history with DoD reporting timeline compliance metrics."""
    return {
        "total_incidents": len(_ops.incidents),
        "open_incidents": sum(1 for i in _ops.incidents if i.state == IncidentState.OPEN),
        "avg_time_to_detect_mins": (
            round(
                sum(i.time_to_detect_mins for i in _ops.incidents)
                / len(_ops.incidents),
                1,
            )
            if _ops.incidents
            else 0
        ),
        "incidents": [
            {
                "incident_id": i.incident_id,
                "title": i.title,
                "severity": i.severity,
                "state": i.state,
                "detected_at": i.detected_at.isoformat(),
                "time_to_detect_mins": i.time_to_detect_mins,
                "time_to_report_mins": i.time_to_report_mins,
                "time_to_contain_mins": i.time_to_contain_mins,
                "affected_controls": i.affected_controls,
                "lessons_learned": i.lessons_learned,
            }
            for i in _ops.incidents
        ],
    }
