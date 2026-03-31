"""
Governance Agent - ZT Visibility & Analytics + Automation & Orchestration Pillars
AGI Corporation 2026

Aligns with CMMC Security Assessment (CA), Risk Assessment (RA), and
Incident Response (IR) domains. Fulcrum LOE 4 - Risk management and
compliance governance.

Responsibilities: policy documentation status, risk assessment findings,
C3PAO readiness gap analysis, POA&M prioritization.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, AssessmentRecord, ControlRecord, get_db, get_latest_assessments

GOVERNANCE_CONTROLS = [
    "CA.2.157",
    "CA.2.158",
    "CA.2.159",
    "CA.3.161",
    "CA.3.162",
    "RA.2.141",
    "RA.2.142",
    "RA.2.143",
    "RA.3.144",
    "RA.3.145",
    "IR.2.092",
    "IR.2.093",
    "IR.2.094",
]


class PolicyStatus(str, Enum):
    CURRENT = "current"
    EXPIRING = "expiring"  # within 90 days
    EXPIRED = "expired"
    MISSING = "missing"
    DRAFT = "draft"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PolicyDocument:
    policy_id: str
    name: str
    domain: str
    cmmc_controls: List[str]
    status: PolicyStatus
    last_reviewed: Optional[datetime]
    review_cycle_days: int
    owner: str
    location: str


@dataclass
class RiskFinding:
    risk_id: str
    title: str
    risk_level: RiskLevel
    affected_controls: List[str]
    likelihood: float  # 0-1
    impact: float  # 0-1
    risk_score: float  # likelihood * impact
    mitigation_status: str  # open / in_progress / mitigated / accepted
    target_date: Optional[datetime]


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
    Governance Agent aligned to ZT Visibility & Analytics and
    Automation & Orchestration Pillars.
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.policies: List[PolicyDocument] = []
        self.risk_findings: List[RiskFinding] = []
        if mock_mode:
            self._load_mock_governance()

    def _load_mock_governance(self):
        now = datetime.now(UTC)
        self.policies = [
            PolicyDocument(
                policy_id="pol001",
                name="Information Security Policy",
                domain="CA",
                cmmc_controls=["CA.2.157", "CA.2.158"],
                status=PolicyStatus.CURRENT,
                last_reviewed=now - timedelta(days=60),
                review_cycle_days=365,
                owner="CISO",
                location="SharePoint/Policies/InfoSec",
            ),
            PolicyDocument(
                policy_id="pol002",
                name="Risk Management Framework",
                domain="RA",
                cmmc_controls=["RA.2.141", "RA.2.142", "RA.2.143"],
                status=PolicyStatus.EXPIRING,
                last_reviewed=now - timedelta(days=280),
                review_cycle_days=365,
                owner="Risk Officer",
                location="SharePoint/Policies/Risk",
            ),
            PolicyDocument(
                policy_id="pol003",
                name="Incident Response Plan",
                domain="IR",
                cmmc_controls=["IR.2.092", "IR.2.093", "IR.2.094"],
                status=PolicyStatus.CURRENT,
                last_reviewed=now - timedelta(days=120),
                review_cycle_days=365,
                owner="SOC Manager",
                location="SharePoint/Policies/IRP",
            ),
            PolicyDocument(
                policy_id="pol004",
                name="System Security Plan (SSP)",
                domain="CA",
                cmmc_controls=["CA.2.157", "CA.2.158", "CA.2.159"],
                status=PolicyStatus.DRAFT,
                last_reviewed=now - timedelta(days=30),
                review_cycle_days=365,
                owner="ISSO",
                location="Confluence/SSP",
            ),
            PolicyDocument(
                policy_id="pol005",
                name="Privacy Policy and CUI Handling",
                domain="CA",
                cmmc_controls=["CA.3.161", "CA.3.162"],
                status=PolicyStatus.MISSING,
                last_reviewed=None,
                review_cycle_days=365,
                owner="Unassigned",
                location="",
            ),
        ]
        self.risk_findings = [
            RiskFinding(
                risk_id="risk001",
                title="Privileged Account MFA Gap",
                risk_level=RiskLevel.CRITICAL,
                affected_controls=["IA.3.083", "IA.3.084", "AC.2.006"],
                likelihood=0.8,
                impact=0.9,
                risk_score=0.72,
                mitigation_status="in_progress",
                target_date=now + timedelta(days=30),
            ),
            RiskFinding(
                risk_id="risk002",
                title="Legacy Server Patch Debt",
                risk_level=RiskLevel.HIGH,
                affected_controls=["CM.3.068", "SI.1.210"],
                likelihood=0.7,
                impact=0.7,
                risk_score=0.49,
                mitigation_status="open",
                target_date=now + timedelta(days=60),
            ),
            RiskFinding(
                risk_id="risk003",
                title="Incomplete Audit Log Coverage",
                risk_level=RiskLevel.MEDIUM,
                affected_controls=["AU.2.041", "AU.2.042"],
                likelihood=0.5,
                impact=0.6,
                risk_score=0.30,
                mitigation_status="in_progress",
                target_date=now + timedelta(days=45),
            ),
            RiskFinding(
                risk_id="risk004",
                title="SSP Not Finalized",
                risk_level=RiskLevel.HIGH,
                affected_controls=["CA.2.157", "CA.2.158"],
                likelihood=1.0,
                impact=0.5,
                risk_score=0.50,
                mitigation_status="open",
                target_date=now + timedelta(days=90),
            ),
        ]

    def check_policy_documentation(self) -> GovernanceAssessmentResult:
        """Assess CA.2.157 / CA.2.158 - Security assessment policies."""
        current = [p for p in self.policies if p.status == PolicyStatus.CURRENT]
        missing = [p for p in self.policies if p.status == PolicyStatus.MISSING]
        expired = [
            p
            for p in self.policies
            if p.status in (PolicyStatus.EXPIRED, PolicyStatus.EXPIRING)
        ]
        draft = [p for p in self.policies if p.status == PolicyStatus.DRAFT]

        findings = []
        remediation = []

        if missing:
            names = [p.name for p in missing]
            findings.append(f"Required policy documents missing: {names}")
            remediation.append(
                "Author and formally approve missing policies; assign owners and review cycles"
            )
        if expired:
            names = [p.name for p in expired]
            findings.append(f"Policies expiring or expired: {names}")
            remediation.append(
                "Initiate annual review cycle; obtain formal management approval"
            )
        if draft:
            names = [p.name for p in draft]
            findings.append(f"Policies still in draft status: {names}")
            remediation.append(
                "Complete review and publish draft policies; integrate into SSP"
            )

        total = len(self.policies)
        confidence = len(current) / total if total > 0 else 0.0
        status = (
            "implemented"
            if confidence >= 0.9
            else (
                "partially_implemented" if confidence >= 0.5 else "not_implemented"
            )
        )

        return GovernanceAssessmentResult(
            control_id="CA.2.157",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_risk_assessment(self) -> GovernanceAssessmentResult:
        """Assess RA.2.141 / RA.2.142 - Risk assessment process and currency."""
        open_critical = [
            r
            for r in self.risk_findings
            if r.risk_level == RiskLevel.CRITICAL
            and r.mitigation_status == "open"
        ]
        overdue = [
            r
            for r in self.risk_findings
            if r.target_date and r.target_date < datetime.now(UTC)
            and r.mitigation_status not in ("mitigated", "accepted")
        ]
        mitigated = [
            r for r in self.risk_findings if r.mitigation_status == "mitigated"
        ]

        findings = []
        remediation = []

        if open_critical:
            titles = [r.title for r in open_critical]
            findings.append(f"Critical risks with no active mitigation: {titles}")
            remediation.append(
                "Immediately initiate POA&M entries for critical risks; assign owners and 30-day targets"
            )
        if overdue:
            titles = [r.title for r in overdue]
            findings.append(f"Risk mitigation actions past target date: {titles}")
            remediation.append(
                "Review and update POA&M milestones; escalate overdue items to senior leadership"
            )
        if not self.risk_findings:
            findings.append("No formal risk register found")
            remediation.append(
                "Establish a risk register with annual assessment cadence per NIST RMF"
            )

        total = len(self.risk_findings)
        mitigation_ratio = len(mitigated) / total if total else 0.0
        open_critical_penalty = len(open_critical) * 0.2
        confidence = max(0.0, 0.5 + mitigation_ratio * 0.5 - open_critical_penalty)

        status = (
            "implemented"
            if confidence >= 0.85
            else (
                "partially_implemented" if confidence >= 0.4 else "not_implemented"
            )
        )

        return GovernanceAssessmentResult(
            control_id="RA.2.141",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    async def check_c3pao_readiness(self, db: AsyncSession) -> GovernanceAssessmentResult:
        """Assess CA.2.159 / CA.3.161 - C3PAO assessment readiness."""
        assessments_map = await get_latest_assessments(db)
        result = await db.execute(select(ControlRecord))
        controls = result.scalars().all()

        total = len(controls)
        implemented = sum(
            1
            for c in controls
            if assessments_map.get(c.id) and assessments_map[c.id].status == "implemented"
        )
        not_assessed = sum(1 for c in controls if c.id not in assessments_map)

        implemented_pct = (implemented / total * 100) if total else 0

        findings = []
        remediation = []

        if implemented_pct < 70:
            findings.append(
                f"Only {implemented_pct:.1f}% of controls implemented — below C3PAO readiness threshold (70%)"
            )
            remediation.append(
                "Prioritize implementation of Level 1 controls and high-SPRS-weight Level 2 controls"
            )
        if not_assessed > 0:
            findings.append(f"{not_assessed} controls have no assessment records")
            remediation.append(
                "Complete initial assessment sweep; document status for all controls in the SSP"
            )

        confidence = min(1.0, implemented_pct / 100)
        status = (
            "implemented"
            if confidence >= 0.85
            else (
                "partially_implemented" if confidence >= 0.5 else "not_implemented"
            )
        )

        return GovernanceAssessmentResult(
            control_id="CA.2.159",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    async def generate_poam_priorities(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Generate prioritized POA&M entries from the current risk register
        and unimplemented controls.
        """
        assessments_map = await get_latest_assessments(db)
        result = await db.execute(select(ControlRecord))
        controls = result.scalars().all()

        poam_items = []

        # Add risk-register-driven items
        for risk in self.risk_findings:
            if risk.mitigation_status not in ("mitigated", "accepted"):
                poam_items.append(
                    {
                        "source": "risk_register",
                        "risk_id": risk.risk_id,
                        "title": risk.title,
                        "risk_level": risk.risk_level,
                        "risk_score": risk.risk_score,
                        "affected_controls": risk.affected_controls,
                        "mitigation_status": risk.mitigation_status,
                        "target_date": (
                            risk.target_date.strftime("%Y-%m-%d")
                            if risk.target_date
                            else "TBD"
                        ),
                        "priority": (
                            1
                            if risk.risk_level == RiskLevel.CRITICAL
                            else 2
                            if risk.risk_level == RiskLevel.HIGH
                            else 3
                        ),
                    }
                )

        # Add controls with no implementation
        for c in controls:
            a = assessments_map.get(c.id)
            if not a or a.status in ("not_implemented", "not_started"):
                poam_items.append(
                    {
                        "source": "control_gap",
                        "control_id": c.id,
                        "title": f"Implement {c.title}",
                        "domain": c.domain,
                        "level": c.level,
                        "risk_level": (
                            "high" if c.level == "Level 1" else "medium"
                        ),
                        "mitigation_status": "open",
                        "target_date": "TBD",
                        "priority": 1 if c.level == "Level 1" else 2,
                    }
                )

        # Sort by priority then risk score (desc)
        poam_items.sort(
            key=lambda x: (x["priority"], -x.get("risk_score", 0))
        )
        return poam_items

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all Governance assessments and return evidence-ready results."""
        sync_assessments = [
            self.check_policy_documentation(),
            self.check_risk_assessment(),
        ]
        async_assessment = await self.check_c3pao_readiness(db)
        all_assessments = sync_assessments + [async_assessment]

        zt_map = {
            "CA.2.157": "Visibility & Analytics",
            "RA.2.141": "Visibility & Analytics",
            "CA.2.159": "Automation & Orchestration",
        }

        results = []
        for a in all_assessments:
            results.append(
                {
                    "control_id": a.control_id,
                    "zt_pillar": zt_map.get(a.control_id, "Visibility & Analytics"),
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
            scope="Visibility & Analytics / Automation Pillars",
            controls_evaluated=[a.control_id for a in all_assessments],
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


@router.get(
    "/assess",
    summary="Run full Governance assessment (ZT Visibility & Automation Pillars)",
)
async def run_governance_assessment(db: AsyncSession = Depends(get_db)):
    """Policy status, risk register, C3PAO readiness — ZT Visibility & Automation."""
    results = await _governance.run_full_assessment(db)
    return {
        "agent": "governance",
        "zt_pillars": ["Visibility & Analytics", "Automation & Orchestration"],
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/risk-posture", summary="Get current risk register and risk scores")
async def get_risk_posture():
    """Return the risk register with risk scores, levels, and mitigation status."""
    total = len(_governance.risk_findings)
    open_risks = [
        r
        for r in _governance.risk_findings
        if r.mitigation_status not in ("mitigated", "accepted")
    ]
    critical = [
        r for r in open_risks if r.risk_level == RiskLevel.CRITICAL
    ]

    return {
        "total_risks": total,
        "open_risks": len(open_risks),
        "critical_open": len(critical),
        "average_risk_score": (
            round(
                sum(r.risk_score for r in open_risks) / len(open_risks), 2
            )
            if open_risks
            else 0
        ),
        "risks": [
            {
                "risk_id": r.risk_id,
                "title": r.title,
                "risk_level": r.risk_level,
                "risk_score": r.risk_score,
                "affected_controls": r.affected_controls,
                "mitigation_status": r.mitigation_status,
                "target_date": (
                    r.target_date.strftime("%Y-%m-%d") if r.target_date else None
                ),
            }
            for r in _governance.risk_findings
        ],
    }


@router.get("/policies", summary="Get policy document inventory and review status")
async def get_policies():
    """Return policy inventory with review status and owner information."""
    total = len(_governance.policies)
    current = sum(1 for p in _governance.policies if p.status == PolicyStatus.CURRENT)

    return {
        "total_policies": total,
        "current": current,
        "coverage_pct": round(current / total * 100, 1) if total else 0,
        "policies": [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "domain": p.domain,
                "status": p.status,
                "last_reviewed": (
                    p.last_reviewed.strftime("%Y-%m-%d")
                    if p.last_reviewed
                    else None
                ),
                "owner": p.owner,
                "cmmc_controls": p.cmmc_controls,
            }
            for p in _governance.policies
        ],
    }


@router.get(
    "/poam-priorities",
    summary="Generate prioritized POA&M items from risk register and control gaps",
)
async def get_poam_priorities(db: AsyncSession = Depends(get_db)):
    """Return prioritized POA&M items integrating risk findings and control gaps."""
    items = await _governance.generate_poam_priorities(db)
    return {
        "total_items": len(items),
        "critical_items": sum(1 for i in items if i.get("priority") == 1),
        "poam_items": items,
        "generated_at": datetime.now(UTC).isoformat(),
    }
