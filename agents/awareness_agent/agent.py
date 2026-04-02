"""
Awareness & Training Agent — CMMC Compliance Platform
AGI Corporation 2026

Covers Awareness & Training (AT) and Personnel Security (PS) controls.
Maps to the DoD Zero Trust User Pillar.

Domains covered:
    AT  (Awareness & Training)  — AT.2.056, AT.2.057, AT.3.058
    PS  (Personnel Security)    — PS.2.127, PS.2.128

Total: 5 controls (AWARENESS_CONTROLS list below)
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

# ---------------------------------------------------------------------------
# Controls owned by this agent
# ---------------------------------------------------------------------------

AWARENESS_CONTROLS: List[str] = [
    # Awareness & Training
    "AT.2.056",
    "AT.2.057",
    "AT.3.058",
    # Personnel Security
    "PS.2.127",
    "PS.2.128",
]


@dataclass
class AwarenessResult:
    control_id: str
    zt_pillar: str
    status: str
    confidence: float
    findings: List[str]
    remediation: List[str]
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    owner_agent: str = "awareness"


# ---------------------------------------------------------------------------
# Mock training & personnel data
# ---------------------------------------------------------------------------

_MOCK_TRAINING_DATA = {
    "annual_security_training_pct": 0.92,   # 92 % of users completed annual training
    "role_based_training_configured": True,  # role-specific training tracks exist
    "insider_threat_training_pct": 0.75,     # 75 % completed insider-threat module
    "personnel_screening_policy": True,      # background check policy documented
    "termination_procedure_documented": True,  # offboarding procedure exists
}


class AwarenessAgent:
    """
    Awareness & Training agent aligned to ZT User Pillar.
    Evaluates security awareness training completion rates and personnel
    security practices.
    """

    def check_security_awareness_training(self) -> AwarenessResult:
        """
        AT.2.056 — Ensure all personnel receive security awareness training.
        """
        pct = _MOCK_TRAINING_DATA["annual_security_training_pct"]
        compliant = pct >= 0.90
        return AwarenessResult(
            control_id="AT.2.056",
            zt_pillar="User",
            status="implemented" if compliant else "partially_implemented",
            confidence=round(min(pct + 0.05, 1.0), 2),
            findings=[
                f"{pct:.0%} of personnel completed annual security awareness training."
            ],
            remediation=[]
            if compliant
            else [
                f"Increase training completion from {pct:.0%} to ≥90 %. "
                "Send reminders and set training deadlines in the LMS."
            ],
        )

    def check_role_based_training(self) -> AwarenessResult:
        """
        AT.2.057 — Provide role-based security training for individuals with
        significant security responsibilities.
        """
        configured = _MOCK_TRAINING_DATA["role_based_training_configured"]
        return AwarenessResult(
            control_id="AT.2.057",
            zt_pillar="User",
            status="implemented" if configured else "not_implemented",
            confidence=0.85 if configured else 0.2,
            findings=[
                "Role-based security training tracks are configured for IT/admin/security roles."
                if configured
                else "No role-based training programme detected."
            ],
            remediation=[]
            if configured
            else [
                "Implement role-based security training for privileged users, "
                "system administrators, and security personnel."
            ],
        )

    def check_insider_threat_training(self) -> AwarenessResult:
        """
        AT.3.058 — Provide security awareness training focused on insider threats.
        """
        pct = _MOCK_TRAINING_DATA["insider_threat_training_pct"]
        compliant = pct >= 0.80
        return AwarenessResult(
            control_id="AT.3.058",
            zt_pillar="User",
            status="implemented" if compliant else "partially_implemented",
            confidence=round(min(pct + 0.05, 1.0), 2),
            findings=[
                f"{pct:.0%} of personnel completed insider-threat awareness training."
            ],
            remediation=[]
            if compliant
            else [
                f"Increase insider-threat training completion from {pct:.0%} to ≥80 %. "
                "Include insider-threat scenarios in annual security awareness content."
            ],
        )

    def check_personnel_screening(self) -> AwarenessResult:
        """
        PS.2.127 — Screen individuals prior to authorizing access to systems.
        """
        policy = _MOCK_TRAINING_DATA["personnel_screening_policy"]
        return AwarenessResult(
            control_id="PS.2.127",
            zt_pillar="User",
            status="implemented" if policy else "not_implemented",
            confidence=0.88 if policy else 0.1,
            findings=[
                "Background check / personnel screening policy is documented and enforced."
                if policy
                else "No formal personnel screening policy found."
            ],
            remediation=[]
            if policy
            else [
                "Document and enforce a personnel screening policy covering "
                "background checks before system access is granted."
            ],
        )

    def check_termination_procedures(self) -> AwarenessResult:
        """
        PS.2.128 — Ensure CUI is protected during and after personnel actions.
        """
        documented = _MOCK_TRAINING_DATA["termination_procedure_documented"]
        return AwarenessResult(
            control_id="PS.2.128",
            zt_pillar="User",
            status="implemented" if documented else "not_implemented",
            confidence=0.82 if documented else 0.15,
            findings=[
                "Termination and transfer procedures are documented and include "
                "access revocation and CUI retrieval steps."
                if documented
                else "No formal offboarding / termination procedure found."
            ],
            remediation=[]
            if documented
            else [
                "Implement an offboarding checklist covering immediate access revocation, "
                "CUI return, and system credential rotation."
            ],
        )

    async def run_full_assessment(
        self,
        db: AsyncSession,
        trigger: str = "manual",
    ) -> List[Dict[str, Any]]:
        """
        Run all awareness and personnel security checks.

        Returns a list of result dicts compatible with the orchestrator / promote schema:
          control_id, zt_pillar, status, confidence, findings, remediation,
          evidence_id, assessed_at, owner_agent
        """
        checks = [
            self.check_security_awareness_training,
            self.check_role_based_training,
            self.check_insider_threat_training,
            self.check_personnel_screening,
            self.check_termination_procedures,
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
            agent_type="awareness",
            trigger=trigger,
            scope="enterprise-awareness",
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
_awareness = AwarenessAgent()


@router.get("/assess", summary="Run full awareness & training assessment")
async def run_awareness_assessment(db: AsyncSession = Depends(get_db)):
    """Run all AT + PS domain checks (awareness training and personnel security)."""
    results = await _awareness.run_full_assessment(db)
    return {
        "agent": "awareness",
        "controls_evaluated": [r["control_id"] for r in results],
        "results": results,
    }
