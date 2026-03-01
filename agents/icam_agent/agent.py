"""
ICAM (Identity, Credential & Access Management) Agent
AGI Corporation 2026

Maps to DoD ZT User Pillar and CMMC Access Control (AC) / Identification &
Authentication (IA) domains. Implements Fulcrum LOE 1 - Identity management.
"""
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import get_db, AgentRunRecord

# CMMC AC + IA controls owned by this agent
ICAM_CONTROLS = [
    "AC.1.001", "AC.1.002", "AC.2.005", "AC.2.006", "AC.2.007",
    "AC.2.008", "AC.2.009", "AC.2.010", "AC.2.011", "AC.2.013",
    "AC.2.015", "AC.2.016", "IA.1.076", "IA.1.077", "IA.2.078",
    "IA.2.079", "IA.2.080", "IA.2.081", "IA.2.082", "IA.3.083",
    "IA.3.084",
]


@dataclass
class UserRecord:
    user_id: str
    username: str
    roles: List[str]
    mfa_enabled: bool
    mfa_type: str  # totp/fido2/sms/none
    last_login: Optional[datetime]
    account_status: str  # active/locked/disabled
    privileged: bool
    department: str
    last_access_review: Optional[datetime]


@dataclass
class ICAMAssessmentResult:
    control_id: str
    status: str
    confidence: float
    findings: List[str]
    evidence_id: str
    remediation: List[str]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ICAMAgent:
    """
    ICAM Agent aligned to ZT User Pillar.
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.users: List[UserRecord] = []
        if mock_mode:
            self._load_mock_users()

    def _load_mock_users(self):
        """Load representative mock user data for demo."""
        self.users = [
            UserRecord(
                user_id="u001", username="alice.admin",
                roles=["SystemAdmin", "CUI_Handler"],
                mfa_enabled=True, mfa_type="fido2",
                last_login=datetime.now(UTC) - timedelta(days=1),
                account_status="active", privileged=True,
                department="IT", last_access_review=datetime.now(UTC) - timedelta(days=30),
            ),
            UserRecord(
                user_id="u002", username="bob.dev",
                roles=["Developer"],
                mfa_enabled=True, mfa_type="totp",
                last_login=datetime.now(UTC) - timedelta(days=2),
                account_status="active", privileged=False,
                department="Engineering", last_access_review=datetime.now(UTC) - timedelta(days=60),
            ),
            UserRecord(
                user_id="u003", username="carol.svc",
                roles=["ServiceAccount"],
                mfa_enabled=False, mfa_type="none",
                last_login=None,
                account_status="active", privileged=True,
                department="Automation", last_access_review=None,
            ),
            UserRecord(
                user_id="u004", username="dave.old",
                roles=["Developer"],
                mfa_enabled=False, mfa_type="none",
                last_login=datetime.now(UTC) - timedelta(days=200),
                account_status="active", privileged=False,
                department="Engineering", last_access_review=datetime.now(UTC) - timedelta(days=400),
            ),
        ]

    def check_mfa_coverage(self) -> ICAMAssessmentResult:
        """Assess IA.3.083 - MFA coverage for all access types."""
        total = len(self.users)
        mfa_users = [u for u in self.users if u.mfa_enabled]
        privileged_users = [u for u in self.users if u.privileged]
        privileged_with_mfa = [u for u in privileged_users if u.mfa_enabled]

        coverage_pct = len(mfa_users) / total if total else 0
        privileged_coverage = len(privileged_with_mfa) / len(privileged_users) if privileged_users else 1

        findings = []
        remediation = []
        if coverage_pct < 1.0:
            missing = [u.username for u in self.users if not u.mfa_enabled]
            findings.append(f"MFA not enabled for {len(missing)} users: {missing}")
            remediation.append("Enroll all users in MFA - enforce via IdP policy")
        if privileged_coverage < 1.0:
            findings.append("Privileged accounts without MFA detected - CRITICAL gap")
            remediation.append("Immediately enroll privileged accounts in FIDO2/hardware MFA")

        confidence = (coverage_pct * 0.5 + privileged_coverage * 0.5)
        status = "implemented" if confidence >= 0.95 else (
            "partially_implemented" if confidence >= 0.5 else "not_implemented"
        )

        return ICAMAssessmentResult(
            control_id="IA.3.083",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_least_privilege(self) -> ICAMAssessmentResult:
        """Assess AC.2.007 - Principle of least privilege."""
        stale_accounts = [
            u for u in self.users
            if u.last_login and (datetime.now(UTC) - u.last_login).days > 90
        ]
        unreviewed = [
            u for u in self.users
            if not u.last_access_review
            or (datetime.now(UTC) - u.last_access_review).days > 365
        ]

        findings = []
        remediation = []
        if stale_accounts:
            findings.append(f"{len(stale_accounts)} accounts inactive >90 days")
            remediation.append("Disable or review stale accounts - automate via JML workflow")
        if unreviewed:
            findings.append(f"{len(unreviewed)} accounts overdue for access review")
            remediation.append("Conduct quarterly access reviews; document in evidence")

        confidence = max(0.0, 1.0 - (len(stale_accounts) + len(unreviewed)) / max(len(self.users), 1) * 0.5)
        status = "implemented" if confidence >= 0.9 else (
            "partially_implemented" if confidence >= 0.6 else "not_implemented"
        )

        return ICAMAssessmentResult(
            control_id="AC.2.007",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    async def run_full_assessment(self, db: AsyncSession, trigger: str = "manual") -> List[Dict[str, Any]]:
        """Run all ICAM assessments and return evidence-ready results."""
        assessments = [
            self.check_mfa_coverage(),
            self.check_least_privilege(),
        ]
        results = []
        for a in assessments:
            results.append({
                "control_id": a.control_id,
                "zt_pillar": "User",
                "status": a.status,
                "confidence": a.confidence,
                "findings": a.findings,
                "remediation": a.remediation,
                "evidence_id": a.evidence_id,
                "assessed_at": a.assessed_at.isoformat(),
                "owner_agent": "icam",
            })

        # Persist result
        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="icam",
            trigger=trigger,
            scope="User Pillar",
            controls_evaluated=[a.control_id for a in assessments],
            findings={"results": results},
            status="completed",
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC)
        )
        db.add(record)
        await db.commit()

        return results


router = APIRouter()
_icam = ICAMAgent(mock_mode=True)


@router.get("/assess", summary="Run full ICAM assessment (ZT User Pillar)")
async def run_icam_assessment(db: AsyncSession = Depends(get_db)):
    """Run ICAM checks for MFA, least privilege, JML - aligned to ZT User Pillar."""
    results = await _icam.run_full_assessment(db)
    return {
        "agent": "icam",
        "zt_pillar": "User",
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/users", summary="List all user records for access review")
async def list_users():
    """Return user inventory for access review evidence."""
    return {
        "total_users": len(_icam.users),
        "mfa_coverage_pct": sum(1 for u in _icam.users if u.mfa_enabled) / len(_icam.users) * 100,
        "privileged_users": sum(1 for u in _icam.users if u.privileged),
        "users": [
            {
                "user_id": u.user_id,
                "username": u.username,
                "roles": u.roles,
                "mfa_enabled": u.mfa_enabled,
                "mfa_type": u.mfa_type,
                "account_status": u.account_status,
                "privileged": u.privileged,
            }
            for u in _icam.users
        ],
    }
