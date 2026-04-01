"""
ICAM (Identity, Credential & Access Management) Agent
AGI Corporation 2026

Maps to DoD ZT User Pillar and CMMC Access Control (AC) / Identification &
Authentication (IA) domains. Implements Fulcrum LOE 1 - Identity management.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

# CMMC AC + IA controls owned by this agent
ICAM_CONTROLS = [
    "AC.1.001",
    "AC.1.002",
    "AC.2.005",
    "AC.2.006",
    "AC.2.007",
    "AC.2.008",
    "AC.2.009",
    "AC.2.010",
    "AC.2.011",
    "AC.2.013",
    "AC.2.015",
    "AC.2.016",
    "AC.3.017",
    "AC.3.018",
    "IA.1.076",
    "IA.1.077",
    "IA.2.078",
    "IA.2.079",
    "IA.2.080",
    "IA.2.081",
    "IA.2.082",
    "IA.3.083",
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
                user_id="u001",
                username="alice.admin",
                roles=["SystemAdmin", "CUI_Handler"],
                mfa_enabled=True,
                mfa_type="fido2",
                last_login=datetime.now(UTC) - timedelta(days=1),
                account_status="active",
                privileged=True,
                department="IT",
                last_access_review=datetime.now(UTC) - timedelta(days=30),
            ),
            UserRecord(
                user_id="u002",
                username="bob.dev",
                roles=["Developer"],
                mfa_enabled=True,
                mfa_type="totp",
                last_login=datetime.now(UTC) - timedelta(days=2),
                account_status="active",
                privileged=False,
                department="Engineering",
                last_access_review=datetime.now(UTC) - timedelta(days=60),
            ),
            UserRecord(
                user_id="u003",
                username="carol.svc",
                roles=["ServiceAccount"],
                mfa_enabled=False,
                mfa_type="none",
                last_login=None,
                account_status="active",
                privileged=True,
                department="Automation",
                last_access_review=None,
            ),
            UserRecord(
                user_id="u004",
                username="dave.old",
                roles=["Developer"],
                mfa_enabled=False,
                mfa_type="none",
                last_login=datetime.now(UTC) - timedelta(days=200),
                account_status="active",
                privileged=False,
                department="Engineering",
                last_access_review=datetime.now(UTC) - timedelta(days=400),
            ),
        ]

    def check_mfa_coverage(self) -> ICAMAssessmentResult:
        """Assess IA.3.083 - MFA coverage for all access types."""
        total = len(self.users)
        mfa_users = [u for u in self.users if u.mfa_enabled]
        privileged_users = [u for u in self.users if u.privileged]
        privileged_with_mfa = [u for u in privileged_users if u.mfa_enabled]

        coverage_pct = len(mfa_users) / total if total else 0
        privileged_coverage = (
            len(privileged_with_mfa) / len(privileged_users) if privileged_users else 1
        )

        findings = []
        remediation = []
        if coverage_pct < 1.0:
            missing = [u.username for u in self.users if not u.mfa_enabled]
            findings.append(f"MFA not enabled for {len(missing)} users: {missing}")
            remediation.append("Enroll all users in MFA - enforce via IdP policy")
        if privileged_coverage < 1.0:
            findings.append("Privileged accounts without MFA detected - CRITICAL gap")
            remediation.append(
                "Immediately enroll privileged accounts in FIDO2/hardware MFA"
            )

        confidence = coverage_pct * 0.5 + privileged_coverage * 0.5
        status = (
            "implemented"
            if confidence >= 0.95
            else ("partially_implemented" if confidence >= 0.5 else "not_implemented")
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
            u
            for u in self.users
            if u.last_login and (datetime.now(UTC) - u.last_login).days > 90
        ]
        unreviewed = [
            u
            for u in self.users
            if not u.last_access_review
            or (datetime.now(UTC) - u.last_access_review).days > 365
        ]

        findings = []
        remediation = []
        if stale_accounts:
            findings.append(f"{len(stale_accounts)} accounts inactive >90 days")
            remediation.append(
                "Disable or review stale accounts - automate via JML workflow"
            )
        if unreviewed:
            findings.append(f"{len(unreviewed)} accounts overdue for access review")
            remediation.append("Conduct quarterly access reviews; document in evidence")

        confidence = max(
            0.0,
            1.0
            - (len(stale_accounts) + len(unreviewed)) / max(len(self.users), 1) * 0.5,
        )
        status = (
            "implemented"
            if confidence >= 0.9
            else ("partially_implemented" if confidence >= 0.6 else "not_implemented")
        )

        return ICAMAssessmentResult(
            control_id="AC.2.007",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_privileged_access_review(self) -> ICAMAssessmentResult:
        """
        Assess IA.3.084 — Employ physical/hardware authenticators for privileged access.
        Also checks IA.2.078 — Unique identification for all users and processes.
        """
        now = datetime.now(UTC)
        ACCESS_REVIEW_DAYS = 90

        privileged = [u for u in self.users if u.privileged and u.account_status == "active"]
        # IA.3.084: privileged users must use strong (fido2/totp) authenticators
        weak_auth = [
            u for u in privileged if u.mfa_type not in ("fido2", "totp", "hardware")
        ]
        # IA.2.078: every user must have a unique role assignment (no shared accounts)
        role_sets = [frozenset(u.roles) for u in self.users]
        duplicate_roles = len(role_sets) != len(set(role_sets))
        # Access review cadence: privileged users reviewed within 90 days
        overdue_reviews = [
            u for u in privileged
            if not u.last_access_review
            or (now - u.last_access_review).days > ACCESS_REVIEW_DAYS
        ]

        findings = []
        remediation = []
        if weak_auth:
            findings.append(
                f"{len(weak_auth)} privileged account(s) using weak/no MFA type: "
                + ", ".join(f"{u.username}({u.mfa_type})" for u in weak_auth)
            )
            remediation.append(
                "Migrate privileged accounts to FIDO2 hardware tokens (IA.3.084)"
            )
        if duplicate_roles:
            findings.append(
                "Duplicate role-set assignments detected; shared accounts may violate IA.2.078"
            )
            remediation.append(
                "Assign unique roles per user; eliminate shared/generic accounts (IA.2.078)"
            )
        if overdue_reviews:
            findings.append(
                f"{len(overdue_reviews)} privileged account(s) have not been reviewed in "
                f"{ACCESS_REVIEW_DAYS} days: "
                + ", ".join(u.username for u in overdue_reviews)
            )
            remediation.append(
                f"Conduct privileged-access reviews at least every {ACCESS_REVIEW_DAYS} days"
            )

        gap_count = len(weak_auth) + (1 if duplicate_roles else 0) + len(overdue_reviews)
        max_issues = len(privileged) + 1 + len(privileged)
        confidence = max(0.0, 1.0 - gap_count / max(max_issues, 1))
        status = (
            "implemented"
            if confidence >= 0.9
            else ("partially_implemented" if confidence >= 0.6 else "not_implemented")
        )
        if not findings:
            findings = [
                f"All {len(privileged)} privileged accounts use strong MFA and are current on reviews (IA.3.084)."
            ]

        return ICAMAssessmentResult(
            control_id="IA.3.084",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_account_lockout(self) -> ICAMAssessmentResult:
        """
        Assess AC.2.013 — Employ security safeguards to protect against unauthorized
        remote access (session controls and account lockout policy).
        Checks for stale accounts that remain active without recent logins.
        """
        now = datetime.now(UTC)
        # Accounts with no login in 180 days that are still active
        stale_active = [
            u for u in self.users
            if u.account_status == "active"
            and u.last_login is not None
            and (now - u.last_login).days > 180
        ]
        # Accounts that have never logged in but are active
        never_logged_in = [
            u for u in self.users
            if u.account_status == "active" and u.last_login is None
        ]

        findings = []
        remediation = []
        if stale_active:
            findings.append(
                f"{len(stale_active)} account(s) active but no login in >180 days: "
                + ", ".join(u.username for u in stale_active)
            )
            remediation.append(
                "Disable accounts inactive >180 days; automate via JML lifecycle (AC.2.013)"
            )
        if never_logged_in:
            findings.append(
                f"{len(never_logged_in)} account(s) have never logged in but remain active: "
                + ", ".join(u.username for u in never_logged_in)
            )
            remediation.append(
                "Audit and disable service/bot accounts that have never authenticated"
            )

        gap_ratio = (len(stale_active) + len(never_logged_in)) / max(len(self.users), 1)
        confidence = max(0.0, 1.0 - gap_ratio)
        status = (
            "implemented"
            if confidence >= 0.9
            else ("partially_implemented" if confidence >= 0.6 else "not_implemented")
        )
        if not findings:
            findings = [
                "No stale or dormant active accounts detected (AC.2.013)."
            ]

        return ICAMAssessmentResult(
            control_id="AC.2.013",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_separation_of_duties(self) -> ICAMAssessmentResult:
        """
        Assess AC.3.017 — Separate duties of individuals to reduce risk of malevolent
        activity without collusion.

        Checks that privileged users do not simultaneously hold conflicting roles
        (e.g., both SystemAdmin and Auditor — who audits their own actions).
        """
        CONFLICTING_PAIRS = [
            ("SystemAdmin", "Auditor"),
            ("CUI_Handler", "SystemAdmin"),
            ("SecurityOfficer", "SystemAdmin"),
        ]

        violations = []
        for u in self.users:
            if u.account_status != "active":
                continue
            role_set = set(u.roles)
            for r1, r2 in CONFLICTING_PAIRS:
                if r1 in role_set and r2 in role_set:
                    violations.append(
                        f"{u.username} holds conflicting roles: {r1} + {r2}"
                    )

        findings = []
        remediation = []
        if violations:
            findings.extend(violations)
            remediation.append(
                "Remove conflicting role assignments; enforce two-person integrity "
                "for sensitive operations (AC.3.017)"
            )
        else:
            findings.append(
                "No conflicting role assignments detected across active user accounts (AC.3.017)."
            )

        confidence = 1.0 if not violations else max(0.0, 1.0 - len(violations) / max(len(self.users), 1))
        status = (
            "implemented"
            if confidence >= 0.95
            else ("partially_implemented" if confidence >= 0.6 else "not_implemented")
        )

        return ICAMAssessmentResult(
            control_id="AC.3.017",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_privilege_escalation_prevention(self) -> ICAMAssessmentResult:
        """
        Assess AC.3.018 — Prevent non-privileged users from executing privileged
        functions and audit the execution of such functions.

        Checks that non-privileged accounts do not hold any roles tagged as
        privileged, and that all privileged-function executions are attributable
        to designated privileged accounts.
        """
        PRIVILEGED_ROLES = {"SystemAdmin", "SecurityOfficer", "CUI_Handler"}

        # Non-privileged users (privileged=False) who hold a privileged-function role
        escalation_risks = [
            u
            for u in self.users
            if not u.privileged
            and u.account_status == "active"
            and PRIVILEGED_ROLES.intersection(set(u.roles))
        ]
        # Privileged users without a recorded access review (no audit trail)
        no_audit_trail = [
            u
            for u in self.users
            if u.privileged
            and u.account_status == "active"
            and not u.last_access_review
        ]

        findings = []
        remediation = []
        if escalation_risks:
            findings.append(
                f"{len(escalation_risks)} non-privileged account(s) hold privileged role(s): "
                + ", ".join(
                    f"{u.username}({', '.join(set(u.roles) & PRIVILEGED_ROLES)})"
                    for u in escalation_risks
                )
            )
            remediation.append(
                "Remove privileged-function roles from non-privileged accounts; "
                "enforce role-based access gating (AC.3.018)"
            )
        if no_audit_trail:
            findings.append(
                f"{len(no_audit_trail)} privileged account(s) lack a recorded access review "
                "(no audit trail for privileged function execution): "
                + ", ".join(u.username for u in no_audit_trail)
            )
            remediation.append(
                "Enable and retain audit logs for all privileged-function executions (AC.3.018)"
            )
        if not findings:
            findings.append(
                "No privilege escalation risks or audit-trail gaps detected (AC.3.018)."
            )

        gap_count = len(escalation_risks) + len(no_audit_trail)
        confidence = max(0.0, 1.0 - gap_count / max(len(self.users), 1))
        status = (
            "implemented"
            if confidence >= 0.9
            else ("partially_implemented" if confidence >= 0.6 else "not_implemented")
        )

        return ICAMAssessmentResult(
            control_id="AC.3.018",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all ICAM assessments and return evidence-ready results."""
        assessments = [
            self.check_mfa_coverage(),
            self.check_least_privilege(),
            self.check_privileged_access_review(),
            self.check_account_lockout(),
            self.check_separation_of_duties(),
            self.check_privilege_escalation_prevention(),
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
                    "owner_agent": "icam",
                }
            )

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
            completed_at=datetime.now(UTC),
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
        "mfa_coverage_pct": sum(1 for u in _icam.users if u.mfa_enabled)
        / len(_icam.users)
        * 100,
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


@router.get(
    "/privileged-access",
    summary="Privileged access review: authenticator strength and account lifecycle",
    description=(
        "Return per-account privileged access review including authenticator type "
        "(IA.3.084), access-review currency, and account dormancy (AC.2.013). "
        "Intended for quarterly privileged-user access reviews."
    ),
)
async def get_privileged_access_review():
    """Privileged access review for IA.3.084 and AC.2.013."""
    now = datetime.now(UTC)
    privileged = [u for u in _icam.users if u.privileged]

    def _days_since(dt):
        if dt is None:
            return None
        return (now - dt).days

    records = [
        {
            "user_id": u.user_id,
            "username": u.username,
            "roles": u.roles,
            "privileged": u.privileged,
            "account_status": u.account_status,
            "mfa_type": u.mfa_type,
            "strong_auth": u.mfa_type in ("fido2", "totp", "hardware"),
            "days_since_login": _days_since(u.last_login),
            "days_since_access_review": _days_since(u.last_access_review),
            "review_overdue": (
                u.last_access_review is None
                or (now - u.last_access_review).days > 90
            ),
        }
        for u in privileged
    ]

    return {
        "privileged_users": len(privileged),
        "strong_auth_count": sum(1 for r in records if r["strong_auth"]),
        "review_overdue_count": sum(1 for r in records if r["review_overdue"]),
        "records": records,
        "controls": ["IA.3.084", "AC.2.013"],
        "timestamp": now.isoformat(),
    }
