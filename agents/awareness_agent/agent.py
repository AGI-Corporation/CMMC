"""
Awareness & Training Agent - ZT User Pillar (Training Dimension)
AGI Corporation 2026

Covers CMMC Awareness and Training (AT) and Personnel Security (PS) domains.
Maps to DoD ZT User Pillar and Fulcrum LOE 1 — workforce readiness.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

# CMMC AT + PS controls owned by this agent
AWARENESS_CONTROLS = [
    "AT.2.056",
    "AT.2.057",
    "AT.3.058",
    "PS.2.127",
    "PS.2.128",
]


@dataclass
class TrainingRecord:
    user_id: str
    username: str
    department: str
    security_awareness_completed: bool
    awareness_completion_date: Optional[datetime]
    role_based_training_completed: bool
    role_training_date: Optional[datetime]
    phishing_simulation_passed: Optional[bool]
    phishing_sim_date: Optional[datetime]


@dataclass
class AwarenessAssessmentResult:
    control_id: str
    status: str
    confidence: float
    findings: List[str]
    evidence_id: str
    remediation: List[str]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AwarenessAgent:
    """
    Awareness & Training Agent aligned to ZT User Pillar.
    Evaluates security awareness programs, role-based training, and social-engineering
    resistance across the workforce.
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.training_records: List[TrainingRecord] = []
        if mock_mode:
            self._load_mock_training_data()

    def _load_mock_training_data(self):
        """Load representative mock training data."""
        now = datetime.now(UTC)
        self.training_records = [
            TrainingRecord(
                user_id="u001",
                username="alice.admin",
                department="IT",
                security_awareness_completed=True,
                awareness_completion_date=now - timedelta(days=30),
                role_based_training_completed=True,
                role_training_date=now - timedelta(days=45),
                phishing_simulation_passed=True,
                phishing_sim_date=now - timedelta(days=15),
            ),
            TrainingRecord(
                user_id="u002",
                username="bob.dev",
                department="Engineering",
                security_awareness_completed=True,
                awareness_completion_date=now - timedelta(days=90),
                role_based_training_completed=True,
                role_training_date=now - timedelta(days=100),
                phishing_simulation_passed=False,
                phishing_sim_date=now - timedelta(days=20),
            ),
            TrainingRecord(
                user_id="u003",
                username="carol.svc",
                department="Automation",
                security_awareness_completed=False,
                awareness_completion_date=None,
                role_based_training_completed=False,
                role_training_date=None,
                phishing_simulation_passed=None,
                phishing_sim_date=None,
            ),
            TrainingRecord(
                user_id="u004",
                username="dave.old",
                department="Engineering",
                security_awareness_completed=True,
                awareness_completion_date=now - timedelta(days=400),
                role_based_training_completed=False,
                role_training_date=None,
                phishing_simulation_passed=None,
                phishing_sim_date=None,
            ),
        ]

    def check_security_awareness_training(self) -> AwarenessAssessmentResult:
        """Assess AT.2.056 - Personnel made aware of security risks."""
        total = len(self.training_records)
        not_trained = [r for r in self.training_records if not r.security_awareness_completed]
        stale_training = [
            r for r in self.training_records
            if r.security_awareness_completed
            and r.awareness_completion_date
            and (datetime.now(UTC) - r.awareness_completion_date).days > 365
        ]

        findings = []
        remediation = []
        if not_trained:
            names = [r.username for r in not_trained]
            findings.append(
                f"{len(not_trained)} personnel have not completed security awareness training: {names}"
            )
            remediation.append(
                "Enroll all personnel in annual security awareness training; track completions"
            )
        if stale_training:
            names = [r.username for r in stale_training]
            findings.append(
                f"{len(stale_training)} personnel have training older than 365 days: {names}"
            )
            remediation.append(
                "Require annual renewal; integrate with HR onboarding/refresh cycles"
            )
        if not findings:
            findings.append(
                "All personnel have current security awareness training on record"
            )

        untrained_count = len(not_trained) + len(stale_training)
        coverage = 1.0 - untrained_count / max(total, 1)
        confidence = round(max(0.0, coverage * 0.9 + 0.1), 2)
        status = (
            "implemented"
            if confidence >= 0.9
            else ("partially_implemented" if confidence >= 0.6 else "not_implemented")
        )
        return AwarenessAssessmentResult(
            control_id="AT.2.056",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_role_based_training(self) -> AwarenessAssessmentResult:
        """Assess AT.2.057 - Personnel adequately trained for their responsibilities."""
        total = len(self.training_records)
        missing_role_training = [
            r for r in self.training_records if not r.role_based_training_completed
        ]

        findings = []
        remediation = []
        if missing_role_training:
            names = [r.username for r in missing_role_training]
            findings.append(
                f"{len(missing_role_training)} personnel lack role-based security training: {names}"
            )
            remediation.append(
                "Implement role-specific training paths (e.g., admin, developer, CUI handler)"
            )
        else:
            findings.append("All personnel have completed role-based training")

        coverage = 1.0 - len(missing_role_training) / max(total, 1)
        confidence = round(max(0.0, coverage), 2)
        status = (
            "implemented"
            if confidence >= 0.9
            else ("partially_implemented" if confidence >= 0.6 else "not_implemented")
        )
        return AwarenessAssessmentResult(
            control_id="AT.2.057",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_threat_recognition_training(self) -> AwarenessAssessmentResult:
        """Assess AT.3.058 - Training on recognizing and reporting threats (social engineering)."""
        total = len(self.training_records)
        # Users who have been sim-tested
        tested = [r for r in self.training_records if r.phishing_simulation_passed is not None]
        failed_sim = [r for r in tested if not r.phishing_simulation_passed]
        not_tested = [r for r in self.training_records if r.phishing_simulation_passed is None]

        findings = []
        remediation = []
        if not_tested:
            names = [r.username for r in not_tested]
            findings.append(
                f"{len(not_tested)} personnel have not been phishing-simulation tested: {names}"
            )
            remediation.append(
                "Run quarterly phishing simulations; provide remedial training for failures"
            )
        if failed_sim:
            names = [r.username for r in failed_sim]
            findings.append(
                f"{len(failed_sim)} personnel failed most recent phishing simulation: {names}"
            )
            remediation.append(
                "Assign immediate remedial social-engineering awareness training to failures"
            )
        if not findings:
            findings.append(
                "Phishing simulation program active; no recent failures detected"
            )

        sim_pass_count = len(tested) - len(failed_sim)
        confidence = round(sim_pass_count / max(total, 1), 2)
        status = (
            "implemented"
            if confidence >= 0.85
            else ("partially_implemented" if confidence >= 0.5 else "not_implemented")
        )
        return AwarenessAssessmentResult(
            control_id="AT.3.058",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all awareness & training assessments and return evidence-ready results."""
        assessments = [
            self.check_security_awareness_training(),
            self.check_role_based_training(),
            self.check_threat_recognition_training(),
        ]

        results = []
        for a in assessments:
            results.append(
                {
                    "control_id": a.control_id,
                    "zt_pillar": "User",
                    "status": a.status,
                    "confidence": a.confidence,
                    "findings": a.findings,
                    "remediation": a.remediation,
                    "evidence_id": a.evidence_id,
                    "assessed_at": a.assessed_at.isoformat(),
                    "owner_agent": "awareness",
                }
            )

        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="awareness",
            trigger=trigger,
            scope="User Pillar - Awareness & Training",
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
_awareness = AwarenessAgent(mock_mode=True)


@router.get("/assess", summary="Run full Awareness & Training assessment (AT/PS domains)")
async def run_awareness_assessment(db: AsyncSession = Depends(get_db)):
    """Run awareness checks for security training, role-based training, and phishing resistance."""
    results = await _awareness.run_full_assessment(db)
    return {
        "agent": "awareness",
        "zt_pillar": "User",
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/training-status", summary="Get training completion status for all personnel")
async def get_training_status():
    """Return training completion summary for all tracked personnel."""
    total = len(_awareness.training_records)
    awareness_complete = sum(
        1 for r in _awareness.training_records if r.security_awareness_completed
    )
    role_training_complete = sum(
        1 for r in _awareness.training_records if r.role_based_training_completed
    )
    phishing_passed = sum(
        1 for r in _awareness.training_records if r.phishing_simulation_passed
    )
    return {
        "total_personnel": total,
        "security_awareness_pct": round(awareness_complete / max(total, 1) * 100, 1),
        "role_based_training_pct": round(role_training_complete / max(total, 1) * 100, 1),
        "phishing_simulation_pass_pct": round(phishing_passed / max(total, 1) * 100, 1),
        "personnel": [
            {
                "user_id": r.user_id,
                "username": r.username,
                "department": r.department,
                "awareness_trained": r.security_awareness_completed,
                "role_trained": r.role_based_training_completed,
                "phishing_sim_passed": r.phishing_simulation_passed,
            }
            for r in _awareness.training_records
        ],
    }
