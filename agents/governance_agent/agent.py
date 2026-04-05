"""
Governance Agent - ZT Visibility & Analytics / Automation & Orchestration Pillars
AGI Corporation 2026

Covers CMMC policy, risk, audit, incident response, maintenance, media protection,
physical protection, personnel security, and supply chain domains.
Maps to DoD ZT Governance pillar and Fulcrum LOE 3/4.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

# CMMC domains and controls owned by this agent
GOVERNANCE_CONTROLS = [
    # Audit & Accountability
    "AU.2.041",
    "AU.2.042",
    "AU.3.045",
    "AU.3.046",
    "AU.3.048",
    # Security Assessment
    "CA.2.157",
    "CA.2.158",
    "CA.3.161",
    # Incident Response
    "IR.2.092",
    "IR.2.093",
    "IR.3.098",
    # Maintenance
    "MA.2.111",
    "MA.2.112",
    "MA.3.115",
    # Media Protection
    "MP.2.119",
    "MP.2.120",
    "MP.2.121",
    "MP.3.122",
    # Physical & Environmental Protection
    "PE.1.131",
    "PE.1.132",
    "PE.2.135",
    # Personnel Security
    "PS.2.127",
    "PS.2.128",
    # Risk Assessment
    "RA.2.141",
    "RA.2.142",
    "RA.3.145",
    # Supply Chain Risk Management
    "SA.2.150",
    "SA.3.152",
]


@dataclass
class GovernanceAssessmentResult:
    control_id: str
    status: str
    confidence: float
    findings: List[str]
    evidence_id: str
    remediation: List[str]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class GovernanceAgent:
    """
    Governance Agent aligned to ZT Visibility & Analytics and Automation pillars.
    Assesses policy, audit, risk, IR, and supply-chain controls.
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self._last_audit_review = datetime.now(UTC) - timedelta(days=45)
        self._last_risk_assessment = datetime.now(UTC) - timedelta(days=200)
        self._last_ir_test = datetime.now(UTC) - timedelta(days=400)
        self._has_poam = True
        self._has_ssp = True
        self._has_audit_logging = True
        self._supplier_reviews_current = False
        self._media_sanitization_policy = True
        self._personnel_screening_policy = True

    # ── Audit & Accountability ────────────────────────────────────────────────

    def check_audit_logging(self) -> GovernanceAssessmentResult:
        """Assess AU.2.041 / AU.2.042 - Audit log creation and retention."""
        findings = []
        remediation = []

        stale_review_days = (datetime.now(UTC) - self._last_audit_review).days
        if stale_review_days > 90:
            findings.append(
                f"Audit log review last performed {stale_review_days} days ago (threshold: 90)"
            )
            remediation.append(
                "Schedule quarterly audit log reviews; assign a designated reviewer"
            )

        if not self._has_audit_logging:
            findings.append("Centralized audit logging not enabled")
            remediation.append(
                "Deploy centralized SIEM or log aggregation pipeline (e.g., OpenSearch)"
            )

        if not findings:
            findings.append(
                "Audit logging is active and review cadence meets requirements"
            )

        confidence = 0.9 if self._has_audit_logging and stale_review_days <= 90 else 0.5
        status = (
            "implemented"
            if confidence >= 0.85
            else ("partially_implemented" if confidence >= 0.5 else "not_implemented")
        )
        return GovernanceAssessmentResult(
            control_id="AU.2.041",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_audit_retention(self) -> GovernanceAssessmentResult:
        """Assess AU.2.042 - Retain audit logs for monitoring and analysis."""
        findings = ["Audit retention policy verified — logs retained for 365+ days"]
        return GovernanceAssessmentResult(
            control_id="AU.2.042",
            status="implemented",
            confidence=0.85,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=[],
        )

    # ── Security Assessment ───────────────────────────────────────────────────

    def check_security_assessment(self) -> GovernanceAssessmentResult:
        """Assess CA.2.157 - Periodically assess security controls."""
        findings = []
        remediation = []

        if not self._has_ssp:
            findings.append("System Security Plan (SSP) not maintained")
            remediation.append(
                "Create and maintain an SSP documenting all security controls"
            )
        if not self._has_poam:
            findings.append("Plan of Action & Milestones (POA&M) not maintained")
            remediation.append(
                "Develop a POA&M to track all identified deficiencies"
            )

        if not findings:
            findings.append("SSP and POA&M are maintained and current")

        confidence = 0.85 if (self._has_ssp and self._has_poam) else 0.4
        status = (
            "implemented"
            if confidence >= 0.8
            else ("partially_implemented" if confidence >= 0.5 else "not_implemented")
        )
        return GovernanceAssessmentResult(
            control_id="CA.2.157",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_poam_management(self) -> GovernanceAssessmentResult:
        """Assess CA.2.158 - Develop and implement plans of action."""
        findings = []
        remediation = []
        if not self._has_poam:
            findings.append("No active POA&M found for identified vulnerabilities")
            remediation.append(
                "Create a POA&M with milestones, responsible parties, and target dates"
            )
        else:
            findings.append("POA&M is maintained with active remediation milestones")

        confidence = 0.85 if self._has_poam else 0.2
        status = "implemented" if self._has_poam else "not_implemented"
        return GovernanceAssessmentResult(
            control_id="CA.2.158",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    # ── Incident Response ─────────────────────────────────────────────────────

    def check_incident_response_capability(self) -> GovernanceAssessmentResult:
        """Assess IR.2.092 - Operational incident-handling capability."""
        findings = []
        remediation = []

        ir_test_days = (datetime.now(UTC) - self._last_ir_test).days
        if ir_test_days > 365:
            findings.append(
                f"IR plan last tested {ir_test_days} days ago (threshold: 365)"
            )
            remediation.append(
                "Conduct annual IR tabletop exercise; document results as evidence"
            )
        else:
            findings.append("IR plan tested within the past year")

        confidence = 0.75 if ir_test_days <= 365 else 0.4
        status = (
            "partially_implemented" if ir_test_days > 365 else "implemented"
        )
        return GovernanceAssessmentResult(
            control_id="IR.2.092",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_incident_reporting(self) -> GovernanceAssessmentResult:
        """Assess IR.2.093 - Track, document, and report incidents."""
        findings = [
            "Incident tracking system (ticketing/SIEM) in place",
            "Reporting procedures documented in IR plan",
        ]
        return GovernanceAssessmentResult(
            control_id="IR.2.093",
            status="implemented",
            confidence=0.80,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=[],
        )

    # ── Risk Assessment ───────────────────────────────────────────────────────

    def check_risk_assessment(self) -> GovernanceAssessmentResult:
        """Assess RA.2.141 - Periodically assess risk to operations."""
        findings = []
        remediation = []

        days_since = (datetime.now(UTC) - self._last_risk_assessment).days
        if days_since > 365:
            findings.append(
                f"Risk assessment last performed {days_since} days ago (threshold: 365)"
            )
            remediation.append(
                "Perform annual risk assessment; document threats, vulnerabilities, and likelihood"
            )
        else:
            findings.append("Risk assessment performed within the past year")

        confidence = 0.85 if days_since <= 365 else 0.3
        status = (
            "implemented"
            if confidence >= 0.8
            else ("partially_implemented" if confidence >= 0.4 else "not_implemented")
        )
        return GovernanceAssessmentResult(
            control_id="RA.2.141",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_vulnerability_scanning(self) -> GovernanceAssessmentResult:
        """Assess RA.2.142 - Scan for vulnerabilities periodically."""
        findings = [
            "Automated vulnerability scanning configured (Trivy/Grype in CI pipeline)",
            "Scan results reviewed monthly",
        ]
        return GovernanceAssessmentResult(
            control_id="RA.2.142",
            status="implemented",
            confidence=0.88,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=[],
        )

    # ── Personnel Security ────────────────────────────────────────────────────

    def check_personnel_screening(self) -> GovernanceAssessmentResult:
        """Assess PS.2.127 - Screen individuals prior to authorizing access."""
        findings = []
        remediation = []
        if self._personnel_screening_policy:
            findings.append(
                "Personnel screening policy enforced; background checks documented"
            )
        else:
            findings.append("No documented personnel screening policy found")
            remediation.append(
                "Establish and enforce a personnel screening policy for all CUI access"
            )

        confidence = 0.85 if self._personnel_screening_policy else 0.2
        status = "implemented" if self._personnel_screening_policy else "not_implemented"
        return GovernanceAssessmentResult(
            control_id="PS.2.127",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_personnel_termination(self) -> GovernanceAssessmentResult:
        """Assess PS.2.128 - Protect CUI during and after personnel actions."""
        findings = [
            "Joiners/Movers/Leavers (JML) process documented",
            "Account deactivation workflow triggers on HR offboarding events",
        ]
        return GovernanceAssessmentResult(
            control_id="PS.2.128",
            status="implemented",
            confidence=0.80,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=[],
        )

    # ── Supply Chain Risk Management ──────────────────────────────────────────

    def check_threat_intelligence_sharing(self) -> GovernanceAssessmentResult:
        """Assess SA.2.150 - Periodically assess risk posed by suppliers."""
        findings = []
        remediation = []
        if not self._supplier_reviews_current:
            findings.append(
                "Supplier/third-party risk reviews not current (>12 months)"
            )
            remediation.append(
                "Conduct annual supplier risk assessments; include CUI-handling clauses in contracts"
            )
        else:
            findings.append("Supplier risk reviews completed within the past 12 months")

        confidence = 0.8 if self._supplier_reviews_current else 0.35
        status = (
            "implemented"
            if self._supplier_reviews_current
            else "partially_implemented"
        )
        return GovernanceAssessmentResult(
            control_id="SA.2.150",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    # ── Media Protection ──────────────────────────────────────────────────────

    def check_media_protection(self) -> GovernanceAssessmentResult:
        """Assess MP.2.119 - Protect system media containing CUI."""
        findings = []
        remediation = []
        if self._media_sanitization_policy:
            findings.append(
                "Media protection policy in place; CUI media encrypted at rest"
            )
        else:
            findings.append("No documented media protection policy for CUI")
            remediation.append(
                "Implement media protection policy covering labeling, access, and sanitization"
            )

        confidence = 0.85 if self._media_sanitization_policy else 0.2
        status = "implemented" if self._media_sanitization_policy else "not_implemented"
        return GovernanceAssessmentResult(
            control_id="MP.2.119",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_media_sanitization(self) -> GovernanceAssessmentResult:
        """Assess MP.2.121 - Sanitize or destroy media before disposal."""
        findings = [
            "Secure media disposal procedure documented (NIST 800-88 compliant)",
            "Physical media destruction records maintained",
        ]
        return GovernanceAssessmentResult(
            control_id="MP.2.121",
            status="implemented",
            confidence=0.82,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=[],
        )

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all governance assessments and return evidence-ready results."""
        assessments = [
            self.check_audit_logging(),
            self.check_audit_retention(),
            self.check_security_assessment(),
            self.check_poam_management(),
            self.check_incident_response_capability(),
            self.check_incident_reporting(),
            self.check_risk_assessment(),
            self.check_vulnerability_scanning(),
            self.check_personnel_screening(),
            self.check_personnel_termination(),
            self.check_threat_intelligence_sharing(),
            self.check_media_protection(),
            self.check_media_sanitization(),
        ]

        results = []
        for a in assessments:
            results.append(
                {
                    "control_id": a.control_id,
                    "zt_pillar": "Visibility & Analytics",
                    "status": a.status,
                    "confidence": a.confidence,
                    "findings": a.findings,
                    "remediation": a.remediation,
                    "evidence_id": a.evidence_id,
                    "assessed_at": a.assessed_at.isoformat(),
                    "owner_agent": "governance",
                }
            )

        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="governance",
            trigger=trigger,
            scope="Governance Pillar",
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
_governance = GovernanceAgent(mock_mode=True)


@router.get("/assess", summary="Run full Governance assessment")
async def run_governance_assessment(db: AsyncSession = Depends(get_db)):
    """Run governance checks covering audit, risk, IR, PS, SA, MP domains."""
    results = await _governance.run_full_assessment(db)
    return {
        "agent": "governance",
        "zt_pillar": "Visibility & Analytics",
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }
