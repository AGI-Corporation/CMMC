"""
Awareness & Training / Personnel Security Agent
AGI Corporation 2026

Aligns with DoD ZT User Pillar — People & Education dimension.
Covers CMMC Awareness and Training (AT) and Personnel Security (PS) domains.
Fulcrum LOE 1 - Security culture and personnel risk management.

Responsibilities:
- Track security awareness training completion for all personnel
- Validate role-based training (system admins, privileged users, general users)
- Insider-threat recognition training coverage
- Pre-employment / transfer / termination screening (PS.2.127, PS.2.128)
- CUI handling certification records

Maps to CMMC controls:
  AT.2.056  Awareness training — security risks
  AT.2.057  Role-based security training
  AT.3.058  Insider threat awareness
  PS.2.127  Pre-employment screening
  PS.2.128  Personnel termination / transfer procedures
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

AWARENESS_CONTROLS = [
    "AT.2.056",
    "AT.2.057",
    "AT.3.058",
    "PS.2.127",
    "PS.2.128",
]


class TrainingStatus(str, Enum):
    CURRENT = "current"
    OVERDUE = "overdue"
    NEVER_COMPLETED = "never_completed"
    EXEMPTED = "exempted"


class PersonnelRole(str, Enum):
    GENERAL_USER = "general_user"
    SYSTEM_ADMIN = "system_admin"
    PRIVILEGED_USER = "privileged_user"
    SECURITY_PERSONNEL = "security_personnel"
    EXECUTIVE = "executive"
    CONTRACTOR = "contractor"


class ScreeningStatus(str, Enum):
    CLEARED = "cleared"
    PENDING = "pending"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class TrainingRecord:
    user_id: str
    name: str
    role: PersonnelRole
    department: str
    # AT.2.056 — general security awareness
    awareness_completed: Optional[datetime] = None
    awareness_due: Optional[datetime] = None
    # AT.2.057 — role-based training
    role_training_completed: Optional[datetime] = None
    role_training_due: Optional[datetime] = None
    # AT.3.058 — insider threat
    insider_threat_completed: Optional[datetime] = None
    insider_threat_due: Optional[datetime] = None
    # PS.2.127 — background check
    screening_status: ScreeningStatus = ScreeningStatus.CLEARED
    screening_date: Optional[datetime] = None
    # PS.2.128 — termination / transfer
    active: bool = True
    termination_date: Optional[datetime] = None
    access_revoked: Optional[datetime] = None


@dataclass
class AwarenessAssessmentResult:
    control_id: str
    status: str  # implemented / partially_implemented / planned / not_implemented
    confidence: float  # 0.0 – 1.0
    findings: List[str] = field(default_factory=list)
    evidence_id: Optional[str] = None


class AwarenessAgent:
    """
    Assesses CMMC Awareness & Training and Personnel Security controls.
    In production this would integrate with an LMS (e.g. KnowBe4, Absorb LMS),
    HRIS, and identity directory (Okta, AD). In mock mode it runs against
    synthetic data representative of a mid-size DoD contractor.
    """

    TRAINING_VALIDITY_DAYS = 365  # annual recurrence
    INSIDER_THREAT_VALIDITY_DAYS = 365
    SCREENING_VALIDITY_DAYS = 3 * 365  # 3-year reinvestigation cycle

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.records: List[TrainingRecord] = []
        if mock_mode:
            self._load_mock_records()

    def _load_mock_records(self) -> None:
        now = datetime.now(UTC)
        self.records = [
            # Fully current personnel
            TrainingRecord(
                user_id="USR-001",
                name="Alice Chen",
                role=PersonnelRole.SYSTEM_ADMIN,
                department="IT Operations",
                awareness_completed=now - timedelta(days=30),
                awareness_due=now + timedelta(days=335),
                role_training_completed=now - timedelta(days=30),
                role_training_due=now + timedelta(days=335),
                insider_threat_completed=now - timedelta(days=30),
                insider_threat_due=now + timedelta(days=335),
                screening_status=ScreeningStatus.CLEARED,
                screening_date=now - timedelta(days=180),
            ),
            # Overdue role-based training
            TrainingRecord(
                user_id="USR-002",
                name="Bob Martinez",
                role=PersonnelRole.PRIVILEGED_USER,
                department="Engineering",
                awareness_completed=now - timedelta(days=400),
                awareness_due=now - timedelta(days=35),
                role_training_completed=now - timedelta(days=400),
                role_training_due=now - timedelta(days=35),
                insider_threat_completed=now - timedelta(days=400),
                insider_threat_due=now - timedelta(days=35),
                screening_status=ScreeningStatus.CLEARED,
                screening_date=now - timedelta(days=600),
            ),
            # Never completed insider threat training
            TrainingRecord(
                user_id="USR-003",
                name="Carol Davis",
                role=PersonnelRole.GENERAL_USER,
                department="Finance",
                awareness_completed=now - timedelta(days=90),
                awareness_due=now + timedelta(days=275),
                role_training_completed=now - timedelta(days=90),
                role_training_due=now + timedelta(days=275),
                insider_threat_completed=None,  # never done
                insider_threat_due=None,
                screening_status=ScreeningStatus.CLEARED,
                screening_date=now - timedelta(days=365),
            ),
            # Contractor pending screening
            TrainingRecord(
                user_id="USR-004",
                name="David Kim",
                role=PersonnelRole.CONTRACTOR,
                department="Consulting",
                awareness_completed=now - timedelta(days=10),
                awareness_due=now + timedelta(days=355),
                role_training_completed=None,  # contractor — role training pending
                role_training_due=now + timedelta(days=7),
                insider_threat_completed=now - timedelta(days=10),
                insider_threat_due=now + timedelta(days=355),
                screening_status=ScreeningStatus.PENDING,
                screening_date=None,
            ),
            # Terminated user — verify access revoked
            TrainingRecord(
                user_id="USR-005",
                name="Eve Thompson",
                role=PersonnelRole.GENERAL_USER,
                department="HR",
                awareness_completed=now - timedelta(days=200),
                awareness_due=now + timedelta(days=165),
                role_training_completed=now - timedelta(days=200),
                role_training_due=now + timedelta(days=165),
                insider_threat_completed=now - timedelta(days=200),
                insider_threat_due=now + timedelta(days=165),
                screening_status=ScreeningStatus.CLEARED,
                screening_date=now - timedelta(days=500),
                active=False,
                termination_date=now - timedelta(days=5),
                access_revoked=now - timedelta(days=5),  # properly revoked
            ),
            # Terminated user — access NOT revoked (gap!)
            TrainingRecord(
                user_id="USR-006",
                name="Frank Lee",
                role=PersonnelRole.PRIVILEGED_USER,
                department="DevOps",
                awareness_completed=now - timedelta(days=100),
                awareness_due=now + timedelta(days=265),
                role_training_completed=now - timedelta(days=100),
                role_training_due=now + timedelta(days=265),
                insider_threat_completed=now - timedelta(days=100),
                insider_threat_due=now + timedelta(days=265),
                screening_status=ScreeningStatus.CLEARED,
                screening_date=now - timedelta(days=200),
                active=False,
                termination_date=now - timedelta(days=3),
                access_revoked=None,  # gap — access not revoked!
            ),
        ]

    # ── AT.2.056: General Security Awareness ────────────────────────────────────

    def check_security_awareness(self) -> AwarenessAssessmentResult:
        """
        AT.2.056 — Ensure personnel are aware of security risks.
        Checks that all active personnel have current annual awareness training.
        """
        now = datetime.now(UTC)
        active = [r for r in self.records if r.active]
        if not active:
            return AwarenessAssessmentResult(
                control_id="AT.2.056",
                status="na",
                confidence=1.0,
                findings=["No active personnel records."],
            )

        overdue = [
            r for r in active
            if r.awareness_due is None or r.awareness_due < now
        ]
        never = [r for r in active if r.awareness_completed is None]
        findings = []
        if never:
            findings.append(
                f"{len(never)} personnel have never completed security awareness training: "
                + ", ".join(r.name for r in never)
            )
        if overdue:
            findings.append(
                f"{len(overdue)} personnel have overdue security awareness training: "
                + ", ".join(r.name for r in overdue)
            )

        current_count = len(active) - len(
            {r.user_id for r in overdue} | {r.user_id for r in never}
        )
        coverage = current_count / len(active) if active else 0.0
        if coverage >= 0.95:
            status, confidence = "implemented", 0.92
        elif coverage >= 0.80:
            status, confidence = "partially_implemented", 0.65
        elif coverage >= 0.50:
            status, confidence = "partially_implemented", 0.40
        else:
            status, confidence = "not_implemented", 0.15

        if not findings:
            findings = [
                f"All {len(active)} active personnel have current security awareness training (AT.2.056)."
            ]

        return AwarenessAssessmentResult(
            control_id="AT.2.056",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
        )

    # ── AT.2.057: Role-Based Security Training ─────────────────────────────────

    def check_role_based_training(self) -> AwarenessAssessmentResult:
        """
        AT.2.057 — Role-based training for system administrators,
        privileged users, and security personnel.
        """
        now = datetime.now(UTC)
        privileged_roles = {
            PersonnelRole.SYSTEM_ADMIN,
            PersonnelRole.PRIVILEGED_USER,
            PersonnelRole.SECURITY_PERSONNEL,
        }
        privileged = [
            r for r in self.records
            if r.active and r.role in privileged_roles
        ]

        if not privileged:
            return AwarenessAssessmentResult(
                control_id="AT.2.057",
                status="na",
                confidence=1.0,
                findings=["No privileged role personnel found."],
            )

        overdue = [
            r for r in privileged
            if r.role_training_due is None or r.role_training_due < now
        ]
        never_trained = [r for r in privileged if r.role_training_completed is None]

        findings = []
        if never_trained:
            findings.append(
                f"{len(never_trained)} privileged users have never completed role-based training: "
                + ", ".join(r.name for r in never_trained)
            )
        if overdue:
            never_ids = {r.user_id for r in never_trained}
            gap_names = [r.name for r in overdue if r.user_id not in never_ids]
            if gap_names:
                findings.append(
                    f"{len(gap_names)} privileged users have overdue role-based training: "
                    + ", ".join(gap_names)
                )

        current = len(privileged) - len(
            {r.user_id for r in overdue} | {r.user_id for r in never_trained}
        )
        coverage = current / len(privileged) if privileged else 0.0
        if coverage >= 0.95:
            status, confidence = "implemented", 0.90
        elif coverage >= 0.80:
            status, confidence = "partially_implemented", 0.65
        else:
            status, confidence = "not_implemented", 0.20

        if not findings:
            findings = [
                f"All {len(privileged)} privileged users have current role-based training (AT.2.057)."
            ]

        return AwarenessAssessmentResult(
            control_id="AT.2.057",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
        )

    # ── AT.3.058: Insider Threat Awareness ─────────────────────────────────────

    def check_insider_threat_training(self) -> AwarenessAssessmentResult:
        """
        AT.3.058 — Insider threat recognition and reporting training.
        Required for all personnel with access to CUI systems.
        """
        now = datetime.now(UTC)
        active = [r for r in self.records if r.active]

        overdue = [
            r for r in active
            if r.insider_threat_due is None or r.insider_threat_due < now
        ]
        never = [r for r in active if r.insider_threat_completed is None]

        findings = []
        if never:
            findings.append(
                f"{len(never)} personnel have never completed insider threat awareness training: "
                + ", ".join(r.name for r in never)
            )
        if overdue:
            never_ids = {r.user_id for r in never}
            gap_names = [r.name for r in overdue if r.user_id not in never_ids]
            if gap_names:
                findings.append(
                    f"{len(gap_names)} personnel have overdue insider threat training: "
                    + ", ".join(gap_names)
                )

        gap_total = len({r.user_id for r in overdue} | {r.user_id for r in never})
        current = len(active) - gap_total
        coverage = current / len(active) if active else 0.0
        if coverage >= 0.95:
            status, confidence = "implemented", 0.90
        elif coverage >= 0.75:
            status, confidence = "partially_implemented", 0.55
        else:
            status, confidence = "not_implemented", 0.20

        if not findings:
            findings = [
                f"All {len(active)} active personnel have current insider threat training (AT.3.058)."
            ]

        return AwarenessAssessmentResult(
            control_id="AT.3.058",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
        )

    # ── PS.2.127: Pre-Employment Screening ─────────────────────────────────────

    def check_pre_employment_screening(self) -> AwarenessAssessmentResult:
        """
        PS.2.127 — Screen individuals prior to authorizing access to systems
        containing CUI.
        """
        all_records = self.records  # includes inactive/terminated
        unscreened = [
            r for r in all_records
            if r.screening_status in {ScreeningStatus.PENDING, ScreeningStatus.FAILED}
            and r.active
        ]
        expired = [
            r for r in all_records
            if r.screening_status == ScreeningStatus.CLEARED
            and r.screening_date is not None
            and (datetime.now(UTC) - r.screening_date).days > self.SCREENING_VALIDITY_DAYS
            and r.active
        ]

        findings = []
        if unscreened:
            findings.append(
                f"{len(unscreened)} active personnel lack cleared background screening: "
                + ", ".join(r.name for r in unscreened)
            )
        if expired:
            findings.append(
                f"{len(expired)} personnel have expired background screening (>{self.SCREENING_VALIDITY_DAYS//365}yr): "
                + ", ".join(r.name for r in expired)
            )

        active = [r for r in self.records if r.active]
        gap_total = len({r.user_id for r in unscreened} | {r.user_id for r in expired})
        cleared = len(active) - gap_total
        coverage = cleared / len(active) if active else 1.0

        if coverage >= 0.95:
            status, confidence = "implemented", 0.88
        elif coverage >= 0.80:
            status, confidence = "partially_implemented", 0.60
        else:
            status, confidence = "not_implemented", 0.20

        if not findings:
            findings = [
                f"All {len(active)} active personnel have cleared background screening (PS.2.127)."
            ]

        return AwarenessAssessmentResult(
            control_id="PS.2.127",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
        )

    # ── PS.2.128: Personnel Termination / Transfer ──────────────────────────────

    def check_termination_procedures(self) -> AwarenessAssessmentResult:
        """
        PS.2.128 — Ensure CUI systems are protected during and after personnel
        actions such as terminations and transfers.
        Checks that access is revoked on or before termination date.
        """
        terminated = [r for r in self.records if not r.active]

        gaps = [
            r for r in terminated
            if r.access_revoked is None
            or (r.termination_date and r.access_revoked > r.termination_date + timedelta(hours=24))
        ]

        findings = []
        if gaps:
            findings.append(
                f"{len(gaps)} terminated personnel did not have access revoked promptly: "
                + ", ".join(r.name for r in gaps)
            )

        if not terminated:
            status, confidence = "na", 1.0
            findings = ["No terminated personnel records found."]
        elif not gaps:
            status, confidence = "implemented", 0.95
            findings = [
                f"Access revocation verified for all {len(terminated)} terminated personnel (PS.2.128)."
            ]
        elif len(gaps) / max(len(terminated), 1) <= 0.10:
            status, confidence = "partially_implemented", 0.65
        else:
            status, confidence = "not_implemented", 0.20

        return AwarenessAssessmentResult(
            control_id="PS.2.128",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=str(uuid.uuid4()),
        )

    # ── Full Assessment ─────────────────────────────────────────────────────────

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all AT/PS assessments. Returns a list of per-control result dicts
        (same schema as ICAM/infra/governance agents) so the orchestrator can
        aggregate them with `all_results.extend(results)`.
        Also persists an AgentRunRecord for audit.
        """
        check_results = [
            self.check_security_awareness(),
            self.check_role_based_training(),
            self.check_insider_threat_training(),
            self.check_pre_employment_screening(),
            self.check_termination_procedures(),
        ]

        result_dicts = [
            {
                "control_id": r.control_id,
                "zt_pillar": "User",
                "status": r.status,
                "confidence": r.confidence,
                "findings": r.findings,
                "evidence_id": r.evidence_id,
                "owner_agent": "awareness",
            }
            for r in check_results
        ]

        run_id = str(uuid.uuid4())
        run = AgentRunRecord(
            id=run_id,
            agent_type="awareness",
            trigger=trigger,
            scope="AT+PS domain assessment",
            controls_evaluated=AWARENESS_CONTROLS,
            findings={"results": result_dicts},
            status="completed",
            completed_at=datetime.now(UTC),
        )
        db.add(run)
        await db.commit()
        return result_dicts


# ── FastAPI Router ──────────────────────────────────────────────────────────────

router = APIRouter()
_awareness = AwarenessAgent(mock_mode=True)


@router.get(
    "/assess",
    summary="Run full Awareness & Training / Personnel Security assessment",
    description=(
        "Run a complete AT+PS domain assessment checking security awareness training "
        "completion, role-based training, insider-threat training, pre-employment "
        "screening, and termination access revocation. "
        "Maps to CMMC controls AT.2.056, AT.2.057, AT.3.058, PS.2.127, PS.2.128."
    ),
)
async def run_awareness_assessment(db: AsyncSession = Depends(get_db)):
    results = await _awareness.run_full_assessment(db)
    return {
        "agent": "awareness",
        "zt_pillar": "User",
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/training-status",
    summary="Get per-user security training completion status",
    description=(
        "Return per-user training completion status for all three training categories: "
        "general security awareness (AT.2.056), role-based training (AT.2.057), and "
        "insider threat recognition (AT.3.058)."
    ),
)
async def get_training_status():
    """Return per-user training status across all three AT controls."""
    agent = AwarenessAgent(mock_mode=True)
    now = datetime.now(UTC)

    def _ts(r: TrainingRecord) -> Dict[str, Any]:
        def _status(completed, due):
            if completed is None:
                return TrainingStatus.NEVER_COMPLETED
            if due is None or due < now:
                return TrainingStatus.OVERDUE
            return TrainingStatus.CURRENT

        return {
            "user_id": r.user_id,
            "name": r.name,
            "role": r.role,
            "department": r.department,
            "active": r.active,
            "awareness_status": _status(r.awareness_completed, r.awareness_due),
            "awareness_due": r.awareness_due.isoformat() if r.awareness_due else None,
            "role_training_status": _status(r.role_training_completed, r.role_training_due),
            "role_training_due": r.role_training_due.isoformat() if r.role_training_due else None,
            "insider_threat_status": _status(
                r.insider_threat_completed, r.insider_threat_due
            ),
            "insider_threat_due": r.insider_threat_due.isoformat() if r.insider_threat_due else None,
            "screening_status": r.screening_status,
            "screening_date": r.screening_date.isoformat() if r.screening_date else None,
        }

    return {
        "personnel": [_ts(r) for r in agent.records],
        "summary": {
            "total": len(agent.records),
            "active": sum(1 for r in agent.records if r.active),
            "terminated": sum(1 for r in agent.records if not r.active),
            "awareness_current": sum(
                1
                for r in agent.records
                if r.active and r.awareness_due and r.awareness_due >= now
            ),
            "role_training_current": sum(
                1
                for r in agent.records
                if r.active and r.role_training_due and r.role_training_due >= now
            ),
            "insider_threat_current": sum(
                1
                for r in agent.records
                if r.active and r.insider_threat_due and r.insider_threat_due >= now
            ),
        },
    }


@router.get(
    "/personnel",
    summary="List personnel with screening and termination status",
    description=(
        "Return the full personnel roster with background screening status and "
        "termination/access-revocation details. Maps to PS.2.127 and PS.2.128."
    ),
)
async def list_personnel():
    """Return all personnel records with PS control compliance status."""
    agent = AwarenessAgent(mock_mode=True)
    now = datetime.now(UTC)

    def _ps(r: TrainingRecord) -> Dict[str, Any]:
        screening_age_days = (
            (now - r.screening_date).days if r.screening_date else None
        )
        return {
            "user_id": r.user_id,
            "name": r.name,
            "role": r.role,
            "department": r.department,
            "active": r.active,
            "screening_status": r.screening_status,
            "screening_date": r.screening_date.isoformat() if r.screening_date else None,
            "screening_age_days": screening_age_days,
            "screening_expired": (
                screening_age_days is not None
                and screening_age_days > AwarenessAgent.SCREENING_VALIDITY_DAYS
            ),
            "termination_date": (
                r.termination_date.isoformat() if r.termination_date else None
            ),
            "access_revoked": r.access_revoked.isoformat() if r.access_revoked else None,
            "access_revocation_gap": (
                None
                if r.active or r.access_revoked is None or r.termination_date is None
                else max(0, (r.access_revoked - r.termination_date).total_seconds() / 3600)
            ),
        }

    records = [_ps(r) for r in agent.records]
    return {
        "personnel": records,
        "total": len(records),
        "active": sum(1 for r in records if r["active"]),
        "terminated": sum(1 for r in records if not r["active"]),
        "screening_gaps": sum(
            1
            for r in records
            if r["active"] and r["screening_status"] != ScreeningStatus.CLEARED
        ),
        "termination_gaps": sum(
            1
            for r in records
            if not r["active"] and r["access_revoked"] is None
        ),
    }
