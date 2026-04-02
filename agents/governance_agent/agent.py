"""
Governance Agent — CMMC Compliance Platform
AGI Corporation 2026

Covers the Policy, Risk, Security Assessment, Situational Awareness, and
Incident Response governance controls. Maps to the DoD ZT
Automation & Orchestration / Visibility & Analytics pillars.

Domains covered:
    SA  (Situational Awareness)  — 1 control
    RA  (Risk Assessment)        — 5 controls
    CA  (Security Assessment)    — 4 controls
    IR  (Incident Response)      — 3 controls
    MA  (Maintenance)            — 1+ controls (shared with Ops)

Total: 14 controls (GOVERNANCE_CONTROLS list below)
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

# ---------------------------------------------------------------------------
# Controls owned by this agent
# ---------------------------------------------------------------------------

GOVERNANCE_CONTROLS: List[str] = [
    # Situational Awareness
    "SA.2.150",
    # Risk Assessment
    "RA.2.141",
    "RA.2.142",
    "RA.2.143",
    "RA.3.144",
    "RA.3.145",
    # Security Assessment / CA
    "CA.2.157",
    "CA.2.158",
    "CA.2.159",
    "CA.3.160",
    # Incident Response
    "IR.2.092",
    "IR.2.093",
    "IR.3.098",
    # Maintenance
    "MA.2.111",
]

# ---------------------------------------------------------------------------
# Pydantic-free result dataclass (no runtime Pydantic dependency for agents)
# ---------------------------------------------------------------------------


@dataclass
class GovernanceResult:
    control_id: str
    zt_pillar: str
    status: str           # implemented / partially_implemented / not_implemented
    confidence: float
    findings: List[str]
    remediation: List[str]
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    owner_agent: str = "governance"


# ---------------------------------------------------------------------------
# Mock data representing governance artifact states
# ---------------------------------------------------------------------------

_MOCK_POLICY_CATALOG = {
    "threat_intelligence_sharing": True,    # SA.2.150
    "risk_assessment_conducted": True,      # RA.*
    "risk_assessment_current": False,       # RA.2.143 — last RA > 12 months ago
    "vulnerability_scan_running": True,     # RA.3.144
    "pen_test_conducted": False,            # RA.3.145
    "security_plan_documented": True,       # CA.2.157
    "security_plan_reviewed": False,        # CA.2.158 — not reviewed in past year
    "plan_of_action_managed": True,         # CA.2.159
    "continuous_monitoring_running": True,  # CA.3.160
    "incident_response_plan": True,         # IR.2.092
    "incident_response_tested": False,      # IR.2.093
    "incident_response_reporting": True,    # IR.3.098
    "maintenance_scheduled": True,          # MA.2.111
}

# ZT pillar assignment for each control domain
_DOMAIN_PILLAR = {
    "SA": "Visibility & Analytics",
    "RA": "Visibility & Analytics",
    "CA": "Automation & Orchestration",
    "IR": "Automation & Orchestration",
    "MA": "Device",
}


class GovernanceAgent:
    """
    Governance Agent — assesses policy, risk, and security assessment controls.
    Runs in mock mode (no external GRC system integration required).
    """

    def check_threat_intelligence_sharing(self) -> GovernanceResult:
        """SA.2.150 — Receive cyber threat intelligence from information-sharing forums."""
        sharing = _MOCK_POLICY_CATALOG["threat_intelligence_sharing"]
        return GovernanceResult(
            control_id="SA.2.150",
            zt_pillar="Visibility & Analytics",
            status="implemented" if sharing else "not_implemented",
            confidence=0.85 if sharing else 0.3,
            findings=[
                "Subscribed to CISA AIS and ISACs for threat intel feeds."
                if sharing else "No threat intelligence sharing program configured."
            ],
            remediation=[]
            if sharing
            else ["Subscribe to CISA AIS or relevant ISAC for threat intelligence."],
        )

    def check_risk_assessment(self) -> GovernanceResult:
        """RA.2.141 / RA.2.142 — Risk assessment conducted and risks identified."""
        conducted = _MOCK_POLICY_CATALOG["risk_assessment_conducted"]
        return GovernanceResult(
            control_id="RA.2.141",
            zt_pillar="Visibility & Analytics",
            status="implemented" if conducted else "not_implemented",
            confidence=0.80 if conducted else 0.2,
            findings=["Risk assessment completed in the past 12 months."]
            if conducted
            else ["No formal risk assessment found."],
            remediation=[]
            if conducted
            else ["Conduct an organisational risk assessment per NIST SP 800-30."],
        )

    def check_risk_assessment_currency(self) -> GovernanceResult:
        """RA.2.143 — Remediate risks per risk evaluation."""
        current = _MOCK_POLICY_CATALOG["risk_assessment_current"]
        return GovernanceResult(
            control_id="RA.2.143",
            zt_pillar="Visibility & Analytics",
            status="implemented" if current else "partially_implemented",
            confidence=0.70 if current else 0.45,
            findings=[
                "Risk assessment results are current."
                if current
                else "Risk assessment results are older than 12 months."
            ],
            remediation=[]
            if current
            else ["Update the risk assessment and document remediation plans."],
        )

    def check_vulnerability_scanning(self) -> GovernanceResult:
        """RA.3.144 — Periodically scan for vulnerabilities."""
        scanning = _MOCK_POLICY_CATALOG["vulnerability_scan_running"]
        return GovernanceResult(
            control_id="RA.3.144",
            zt_pillar="Visibility & Analytics",
            status="implemented" if scanning else "not_implemented",
            confidence=0.90 if scanning else 0.1,
            findings=["Automated vulnerability scanning is active."]
            if scanning
            else ["No vulnerability scanning programme detected."],
            remediation=[]
            if scanning
            else ["Deploy vulnerability scanning (e.g. Tenable, Qualys) on a defined schedule."],
        )

    def check_penetration_testing(self) -> GovernanceResult:
        """RA.3.145 — Remediate vulnerabilities via pen testing."""
        tested = _MOCK_POLICY_CATALOG["pen_test_conducted"]
        return GovernanceResult(
            control_id="RA.3.145",
            zt_pillar="Visibility & Analytics",
            status="implemented" if tested else "not_implemented",
            confidence=0.80 if tested else 0.2,
            findings=["Annual penetration test completed."]
            if tested
            else ["No penetration test record found."],
            remediation=[]
            if tested
            else ["Engage a qualified pen testing firm and schedule annual test."],
        )

    def check_security_plan(self) -> GovernanceResult:
        """CA.2.157 — Periodically assess security controls."""
        documented = _MOCK_POLICY_CATALOG["security_plan_documented"]
        return GovernanceResult(
            control_id="CA.2.157",
            zt_pillar="Automation & Orchestration",
            status="implemented" if documented else "not_implemented",
            confidence=0.85 if documented else 0.15,
            findings=["System Security Plan (SSP) is documented and current."]
            if documented
            else ["No SSP found."],
            remediation=[]
            if documented
            else ["Document a System Security Plan per NIST SP 800-18."],
        )

    def check_security_plan_review(self) -> GovernanceResult:
        """CA.2.158 — Develop and implement POA&Ms."""
        reviewed = _MOCK_POLICY_CATALOG["security_plan_reviewed"]
        return GovernanceResult(
            control_id="CA.2.158",
            zt_pillar="Automation & Orchestration",
            status="implemented" if reviewed else "partially_implemented",
            confidence=0.75 if reviewed else 0.40,
            findings=["SSP reviewed within the past year."]
            if reviewed
            else ["SSP has not been reviewed in over 12 months."],
            remediation=[]
            if reviewed
            else ["Schedule annual SSP review and update with security posture changes."],
        )

    def check_poam_management(self) -> GovernanceResult:
        """CA.2.159 — Manage POA&Ms for control deficiencies."""
        managed = _MOCK_POLICY_CATALOG["plan_of_action_managed"]
        return GovernanceResult(
            control_id="CA.2.159",
            zt_pillar="Automation & Orchestration",
            status="implemented" if managed else "not_implemented",
            confidence=0.82 if managed else 0.1,
            findings=["POA&M tracking system is active."]
            if managed
            else ["No POA&M management process found."],
            remediation=[]
            if managed
            else ["Implement POA&M tracking; review and update quarterly."],
        )

    def check_continuous_monitoring(self) -> GovernanceResult:
        """CA.3.160 — Develop / implement a continuous monitoring strategy."""
        running = _MOCK_POLICY_CATALOG["continuous_monitoring_running"]
        return GovernanceResult(
            control_id="CA.3.160",
            zt_pillar="Automation & Orchestration",
            status="implemented" if running else "not_implemented",
            confidence=0.88 if running else 0.15,
            findings=["Continuous monitoring program is operational."]
            if running
            else ["No continuous monitoring program detected."],
            remediation=[]
            if running
            else ["Implement a ConMon program per NIST SP 800-137."],
        )

    def check_ir_plan(self) -> GovernanceResult:
        """IR.2.092 — Establish an incident response capability."""
        ir_plan = _MOCK_POLICY_CATALOG["incident_response_plan"]
        return GovernanceResult(
            control_id="IR.2.092",
            zt_pillar="Automation & Orchestration",
            status="implemented" if ir_plan else "not_implemented",
            confidence=0.88 if ir_plan else 0.1,
            findings=["Incident Response Plan (IRP) is documented."]
            if ir_plan
            else ["No IRP found."],
            remediation=[]
            if ir_plan
            else ["Document an IRP per NIST SP 800-61 Rev 2."],
        )

    def check_ir_testing(self) -> GovernanceResult:
        """IR.2.093 — Track, document, and report incidents."""
        tested = _MOCK_POLICY_CATALOG["incident_response_tested"]
        return GovernanceResult(
            control_id="IR.2.093",
            zt_pillar="Automation & Orchestration",
            status="implemented" if tested else "partially_implemented",
            confidence=0.75 if tested else 0.35,
            findings=["IR tabletop exercise completed in the past year."]
            if tested
            else ["IR plan has not been tested recently."],
            remediation=[]
            if tested
            else ["Conduct an annual IR tabletop exercise and document results."],
        )

    def check_ir_reporting(self) -> GovernanceResult:
        """IR.3.098 — Track and document incidents."""
        reporting = _MOCK_POLICY_CATALOG["incident_response_reporting"]
        return GovernanceResult(
            control_id="IR.3.098",
            zt_pillar="Automation & Orchestration",
            status="implemented" if reporting else "not_implemented",
            confidence=0.82 if reporting else 0.2,
            findings=["Incident reporting procedures and DCSA/DIBNet reporting configured."]
            if reporting
            else ["No formal incident reporting mechanism found."],
            remediation=[]
            if reporting
            else ["Establish incident reporting pipeline to DCSA/DIBNet."],
        )

    def check_maintenance_control(self) -> GovernanceResult:
        """MA.2.111 — Perform maintenance on organizational systems."""
        scheduled = _MOCK_POLICY_CATALOG["maintenance_scheduled"]
        return GovernanceResult(
            control_id="MA.2.111",
            zt_pillar="Device",
            status="implemented" if scheduled else "not_implemented",
            confidence=0.80 if scheduled else 0.2,
            findings=["Scheduled maintenance windows are configured and documented."]
            if scheduled
            else ["No maintenance schedule found."],
            remediation=[]
            if scheduled
            else ["Implement a maintenance schedule and document in the SSP."],
        )

    async def run_full_assessment(
        self,
        db: AsyncSession,
        trigger: str = "manual",
    ) -> List[Dict[str, Any]]:
        """
        Run all governance checks and persist an AgentRunRecord.

        Returns a list of result dicts compatible with the orchestrator schema:
          control_id, zt_pillar, status, confidence, findings, remediation,
          evidence_id, assessed_at, owner_agent
        """
        checks = [
            self.check_threat_intelligence_sharing,
            self.check_risk_assessment,
            self.check_risk_assessment_currency,
            self.check_vulnerability_scanning,
            self.check_penetration_testing,
            self.check_security_plan,
            self.check_security_plan_review,
            self.check_poam_management,
            self.check_continuous_monitoring,
            self.check_ir_plan,
            self.check_ir_testing,
            self.check_ir_reporting,
            self.check_maintenance_control,
        ]

        results = [check() for check in checks]
        result_dicts = [
            {
                "control_id": r.control_id,
                "zt_pillar": r.zt_pillar,
                "status": r.status,
                "confidence": r.confidence,
                "findings": r.findings,
                "remediation": r.remediation,
                "evidence_id": r.evidence_id,
                "assessed_at": r.assessed_at.isoformat(),
                "owner_agent": r.owner_agent,
            }
            for r in results
        ]

        run = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="governance",
            trigger=trigger,
            scope="enterprise-governance",
            controls_evaluated=[r.control_id for r in results],
            findings={"results": result_dicts},
            status="completed",
            completed_at=datetime.now(UTC),
        )
        db.add(run)
        await db.commit()

        return result_dicts


# ---------------------------------------------------------------------------
# FastAPI router
# ---------------------------------------------------------------------------

router = APIRouter()
_governance = GovernanceAgent()


@router.get("/assess", summary="Run full governance assessment")
async def run_governance_assessment(db: AsyncSession = Depends(get_db)):
    """Run all governance policy / risk / CA / IR / MA checks."""
    results = await _governance.run_full_assessment(db)
    return {
        "agent": "governance",
        "controls_evaluated": [r["control_id"] for r in results],
        "results": results,
    }
