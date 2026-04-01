"""
Supply Chain Risk Management (SCRM) Agent
AGI Corporation 2026

Aligns with DoD ZT Application Pillar and CMMC Supply Chain (SR) domain.
Covers the four SR controls added in NIST SP 800-171 Rev 2:
  SR.1.001 - Establish supply chain risk management process
  SR.1.002 - Identify and assess supply chain risks
  SR.2.070 - Manage supply chain risks associated with external system services
  SR.2.111 - Employ safe disposal procedures for system components

Responsibilities:
  - Vendor risk inventory and rating
  - Third-party software / hardware provenance tracking
  - SBOM / dependency supply chain assessment
  - Disposal / sanitization verification
  - Cross-agent evidence sharing for SI, CM, and MA domain overlap
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

# ─── CMMC SR controls owned by this agent ─────────────────────────────────────
SC_CONTROLS = [
    "SR.1.001",  # Supply chain risk management process
    "SR.1.002",  # Identify and assess supply chain risks
    "SR.2.070",  # Manage risks from external system services
    "SR.2.111",  # Safe disposal of system components
]


class VendorTier(str, Enum):
    CRITICAL = "critical"    # Direct CUI data access / processing
    HIGH = "high"            # Significant integration, no direct CUI
    MEDIUM = "medium"        # Indirect / peripheral suppliers
    LOW = "low"              # Commodity vendors, minimal risk


class VendorStatus(str, Enum):
    APPROVED = "approved"
    UNDER_REVIEW = "under_review"
    SUSPENDED = "suspended"
    DECOMMISSIONED = "decommissioned"


@dataclass
class VendorRecord:
    vendor_id: str
    name: str
    tier: VendorTier
    status: VendorStatus
    products: List[str]
    cui_access: bool
    contract_expires: Optional[datetime]
    last_risk_assessment: Optional[datetime]
    risk_score: float           # 0.0 (low risk) to 1.0 (critical risk)
    countries_of_origin: List[str]
    has_sbom: bool
    has_disposal_procedure: bool
    notes: str = ""


@dataclass
class SCRMAssessmentResult:
    control_id: str
    status: str
    confidence: float
    findings: List[str]
    evidence_id: str
    remediation: List[str]
    owner_agent: str = "supply_chain"
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SupplyChainAgent:
    """
    Supply Chain Risk Management agent.
    Implements CMMC SR domain controls, SCRM process checks, and vendor
    risk quantification aligned to DoD ZT Application Pillar.
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.vendors: List[VendorRecord] = []
        self.disposal_records: List[Dict[str, Any]] = []
        if mock_mode:
            self._load_mock_vendors()
            self._load_mock_disposal_records()

    def _load_mock_vendors(self):
        now = datetime.now(UTC)
        self.vendors = [
            VendorRecord(
                vendor_id="v001",
                name="CloudEdge Solutions",
                tier=VendorTier.CRITICAL,
                status=VendorStatus.APPROVED,
                products=["CUI-Cloud Storage", "Encrypted Backup Service"],
                cui_access=True,
                contract_expires=now + timedelta(days=180),
                last_risk_assessment=now - timedelta(days=45),
                risk_score=0.25,
                countries_of_origin=["US"],
                has_sbom=True,
                has_disposal_procedure=True,
                notes="FedRAMP Moderate authorized",
            ),
            VendorRecord(
                vendor_id="v002",
                name="TechFlow Components",
                tier=VendorTier.HIGH,
                status=VendorStatus.APPROVED,
                products=["Network Switches", "Routers"],
                cui_access=False,
                contract_expires=now + timedelta(days=90),
                last_risk_assessment=now - timedelta(days=200),
                risk_score=0.45,
                countries_of_origin=["US", "Taiwan"],
                has_sbom=False,
                has_disposal_procedure=True,
                notes="Hardware components; last assessment overdue",
            ),
            VendorRecord(
                vendor_id="v003",
                name="OpenSource DevTools LLC",
                tier=VendorTier.MEDIUM,
                status=VendorStatus.UNDER_REVIEW,
                products=["CI/CD Pipeline Tools", "Dependency Scanner"],
                cui_access=False,
                contract_expires=now + timedelta(days=365),
                last_risk_assessment=now - timedelta(days=30),
                risk_score=0.60,
                countries_of_origin=["US", "India", "Ukraine"],
                has_sbom=True,
                has_disposal_procedure=False,
                notes="Multi-national development team; no disposal procedure for SaaS",
            ),
            VendorRecord(
                vendor_id="v004",
                name="SecureID Partners",
                tier=VendorTier.CRITICAL,
                status=VendorStatus.APPROVED,
                products=["MFA Hardware Tokens", "Identity Platform"],
                cui_access=True,
                contract_expires=now + timedelta(days=450),
                last_risk_assessment=now - timedelta(days=15),
                risk_score=0.15,
                countries_of_origin=["US"],
                has_sbom=True,
                has_disposal_procedure=True,
                notes="SOC 2 Type II certified; FIDO2 certified tokens",
            ),
            VendorRecord(
                vendor_id="v005",
                name="GlobalParts Ltd",
                tier=VendorTier.HIGH,
                status=VendorStatus.SUSPENDED,
                products=["Server Components", "Memory Modules"],
                cui_access=False,
                contract_expires=now - timedelta(days=10),
                last_risk_assessment=now - timedelta(days=400),
                risk_score=0.85,
                countries_of_origin=["China"],
                has_sbom=False,
                has_disposal_procedure=False,
                notes="SUSPENDED: Country-of-origin risk; pending replacement sourcing",
            ),
        ]

    def _load_mock_disposal_records(self):
        now = datetime.now(UTC)
        self.disposal_records = [
            {
                "record_id": "dr001",
                "asset_type": "Hard Drive",
                "asset_count": 12,
                "method": "NIST SP 800-88 Purge",
                "certified_at": (now - timedelta(days=30)).isoformat(),
                "certifying_authority": "Internal ISSO",
                "cui_bearing": True,
                "compliant": True,
            },
            {
                "record_id": "dr002",
                "asset_type": "Laptop",
                "asset_count": 4,
                "method": "DoD 5220.22-M Wipe",
                "certified_at": (now - timedelta(days=60)).isoformat(),
                "certifying_authority": "IT Security Team",
                "cui_bearing": False,
                "compliant": True,
            },
            {
                "record_id": "dr003",
                "asset_type": "USB Media",
                "asset_count": 30,
                "method": "Physical Destruction",
                "certified_at": (now - timedelta(days=90)).isoformat(),
                "certifying_authority": "External Vendor: SecureShred Inc.",
                "cui_bearing": True,
                "compliant": True,
            },
            {
                "record_id": "dr004",
                "asset_type": "Mobile Device",
                "asset_count": 2,
                "method": "Factory Reset (not verified)",
                "certified_at": (now - timedelta(days=10)).isoformat(),
                "certifying_authority": "Employee self-reported",
                "cui_bearing": True,
                "compliant": False,
            },
        ]

    # ── Control checks ─────────────────────────────────────────────────────────

    def check_scrm_process(self) -> SCRMAssessmentResult:
        """
        SR.1.001 - Establish and maintain a SCRM process.
        Check: Is there a documented SCRM policy covering all vendor tiers?
        """
        findings = []
        remediation = []
        evidence_id = f"ev-scrm-process-{uuid.uuid4().hex[:8]}"

        critical_vendors = [v for v in self.vendors if v.tier == VendorTier.CRITICAL]
        overdue_assessments = [
            v for v in self.vendors
            if v.last_risk_assessment
            and (datetime.now(UTC) - v.last_risk_assessment).days > 365
        ]
        no_assessment = [v for v in self.vendors if v.last_risk_assessment is None]

        if overdue_assessments or no_assessment:
            findings.append(
                f"{len(overdue_assessments)} vendors have overdue risk assessments; "
                f"{len(no_assessment)} have never been assessed."
            )
            remediation.append("Schedule annual vendor risk assessments for all tiers.")

        suspended = [v for v in self.vendors if v.status == VendorStatus.SUSPENDED]
        if suspended:
            findings.append(f"{len(suspended)} vendor(s) suspended pending risk resolution.")
            remediation.append("Complete sourcing replacement for suspended vendors within 90 days.")

        if not findings:
            status = "implemented"
            confidence = 0.88
            findings.append(
                f"SCRM process documented; {len(critical_vendors)} critical vendors active."
            )
        else:
            status = "partially_implemented"
            confidence = 0.60
            remediation.insert(0, "Formalize SCRM policy document and review cycle.")

        return SCRMAssessmentResult(
            control_id="SR.1.001",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=evidence_id,
            remediation=remediation,
        )

    def check_scrm_risk_identification(self) -> SCRMAssessmentResult:
        """
        SR.1.002 - Identify and assess supply chain risks.
        Check: Are all vendors risk-scored? Are country-of-origin risks flagged?
        """
        findings = []
        remediation = []
        evidence_id = f"ev-scrm-risk-{uuid.uuid4().hex[:8]}"

        high_risk_vendors = [v for v in self.vendors if v.risk_score >= 0.70]
        foreign_adversary_countries = {"China", "Russia", "North Korea", "Iran"}
        adversary_vendors = [
            v for v in self.vendors
            if set(v.countries_of_origin) & foreign_adversary_countries
        ]

        no_sbom = [v for v in self.vendors if not v.has_sbom and v.tier in (VendorTier.CRITICAL, VendorTier.HIGH)]

        if adversary_vendors:
            findings.append(
                f"{len(adversary_vendors)} vendor(s) have components from foreign adversary nations: "
                + ", ".join(v.name for v in adversary_vendors)
            )
            remediation.append("Initiate alternative sourcing for foreign adversary-linked vendors.")

        if high_risk_vendors:
            findings.append(
                f"{len(high_risk_vendors)} vendor(s) have risk score ≥ 0.70 and require escalated review."
            )
            remediation.append("Escalate high-risk vendors to CISO for disposition decision.")

        if no_sbom:
            findings.append(
                f"{len(no_sbom)} critical/high-tier vendor(s) lack a Software Bill of Materials (SBOM)."
            )
            remediation.append("Require SBOM submission from all critical and high-tier vendors.")

        if not findings:
            status = "implemented"
            confidence = 0.90
            findings.append("All vendors risk-scored; no foreign adversary country exposure detected.")
        else:
            status = "partially_implemented"
            confidence = 0.55

        return SCRMAssessmentResult(
            control_id="SR.1.002",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=evidence_id,
            remediation=remediation,
        )

    def check_external_services_risk(self) -> SCRMAssessmentResult:
        """
        SR.2.070 - Manage supply chain risks from external system services.
        Check: Are all external services under contract with security requirements?
        """
        findings = []
        remediation = []
        evidence_id = f"ev-scrm-ext-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)

        expiring_soon = [
            v for v in self.vendors
            if v.contract_expires and (v.contract_expires - now).days < 90
        ]
        expired = [
            v for v in self.vendors
            if v.contract_expires and v.contract_expires < now
        ]
        cui_no_contract_assurance = [
            v for v in self.vendors
            if v.cui_access and v.status != VendorStatus.APPROVED
        ]

        if expired:
            findings.append(
                f"{len(expired)} vendor contract(s) have expired: "
                + ", ".join(v.name for v in expired)
            )
            remediation.append("Renew or terminate expired vendor contracts immediately.")

        if expiring_soon:
            findings.append(
                f"{len(expiring_soon)} vendor contract(s) expire within 90 days."
            )
            remediation.append("Initiate renewal process for contracts expiring within 90 days.")

        if cui_no_contract_assurance:
            findings.append(
                f"{len(cui_no_contract_assurance)} CUI-handling vendor(s) are not in approved status."
            )
            remediation.append("Suspend CUI access for non-approved vendors immediately.")

        if not findings:
            status = "implemented"
            confidence = 0.85
            findings.append("All external service contracts current with security provisions.")
        else:
            status = "partially_implemented"
            confidence = 0.65

        return SCRMAssessmentResult(
            control_id="SR.2.070",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=evidence_id,
            remediation=remediation,
        )

    def check_disposal_procedures(self) -> SCRMAssessmentResult:
        """
        SR.2.111 - Employ safe disposal procedures for system components.
        Check: Are all CUI-bearing disposals using certified NIST SP 800-88 methods?
        """
        findings = []
        remediation = []
        evidence_id = f"ev-scrm-disposal-{uuid.uuid4().hex[:8]}"

        cui_disposals = [r for r in self.disposal_records if r["cui_bearing"]]
        non_compliant = [r for r in cui_disposals if not r["compliant"]]
        vendors_no_disposal = [v for v in self.vendors if not v.has_disposal_procedure]

        if non_compliant:
            findings.append(
                f"{len(non_compliant)} CUI-bearing disposal record(s) are non-compliant "
                "(insufficient sanitization method)."
            )
            remediation.append(
                "Require NIST SP 800-88 Purge/Destroy methods for all CUI-bearing media."
            )
            remediation.append(
                "Review and re-sanitize or physically destroy the non-compliant assets."
            )

        if vendors_no_disposal:
            findings.append(
                f"{len(vendors_no_disposal)} vendor(s) lack a documented disposal procedure."
            )
            remediation.append(
                "Add hardware disposal requirements to vendor contracts and verify compliance."
            )

        if not findings:
            status = "implemented"
            confidence = 0.92
            findings.append(
                f"All {len(cui_disposals)} CUI-bearing disposals compliant with NIST SP 800-88."
            )
        else:
            status = "partially_implemented"
            confidence = 0.70

        return SCRMAssessmentResult(
            control_id="SR.2.111",
            status=status,
            confidence=confidence,
            findings=findings,
            evidence_id=evidence_id,
            remediation=remediation,
        )

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all SR domain assessments and return evidence-ready results."""
        checks = [
            self.check_scrm_process(),
            self.check_scrm_risk_identification(),
            self.check_external_services_risk(),
            self.check_disposal_procedures(),
        ]

        results = []
        for check in checks:
            result = {
                "control_id": check.control_id,
                "status": check.status,
                "confidence": check.confidence,
                "findings": check.findings,
                "evidence_id": check.evidence_id,
                "remediation": check.remediation,
                "owner_agent": check.owner_agent,
            }
            results.append(result)

        run_record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="supply_chain",
            trigger=trigger,
            scope="supply-chain-sr-domain",
            controls_evaluated=SC_CONTROLS,
            findings={"results": results},
            status="completed",
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(run_record)
        await db.commit()
        return results


# ─── FastAPI router ────────────────────────────────────────────────────────────

router = APIRouter()
_scrm = SupplyChainAgent(mock_mode=True)


@router.get("/assess", summary="Run full SCRM / SR-domain assessment")
async def assess(db: AsyncSession = Depends(get_db)):
    """
    Execute all SR control checks (SR.1.001, SR.1.002, SR.2.070, SR.2.111)
    and persist findings as an AgentRunRecord.
    """
    results = await _scrm.run_full_assessment(db)
    return {
        "agent": "supply_chain",
        "zt_pillar": "Application",
        "zt_capability": "SCRM / Software Supply Chain",
        "controls_evaluated": SC_CONTROLS,
        "assessments": results,
    }


@router.get("/vendors", summary="List vendor risk inventory")
async def list_vendors(tier: Optional[str] = None, status: Optional[str] = None):
    """
    Return the vendor risk inventory, optionally filtered by tier or status.
    Maps to SR.1.001 (SCRM process) and SR.1.002 (risk identification).
    """
    vendors = _scrm.vendors
    if tier:
        vendors = [v for v in vendors if v.tier.value == tier]
    if status:
        vendors = [v for v in vendors if v.status.value == status]

    return {
        "total_vendors": len(vendors),
        "vendors": [
            {
                "vendor_id": v.vendor_id,
                "name": v.name,
                "tier": v.tier.value,
                "status": v.status.value,
                "risk_score": v.risk_score,
                "cui_access": v.cui_access,
                "has_sbom": v.has_sbom,
                "has_disposal_procedure": v.has_disposal_procedure,
                "countries_of_origin": v.countries_of_origin,
                "contract_expires": v.contract_expires.isoformat()
                if v.contract_expires
                else None,
                "last_risk_assessment": v.last_risk_assessment.isoformat()
                if v.last_risk_assessment
                else None,
                "notes": v.notes,
            }
            for v in vendors
        ],
        "risk_summary": {
            "critical_tier": sum(1 for v in _scrm.vendors if v.tier == VendorTier.CRITICAL),
            "high_risk": sum(1 for v in _scrm.vendors if v.risk_score >= 0.70),
            "suspended": sum(1 for v in _scrm.vendors if v.status == VendorStatus.SUSPENDED),
            "lacking_sbom": sum(1 for v in _scrm.vendors if not v.has_sbom),
        },
    }


@router.get(
    "/analyze-risk/{vendor_id}",
    summary="Detailed risk analysis for a specific vendor",
)
async def analyze_vendor_risk(vendor_id: str):
    """
    Return detailed risk analysis for a vendor, including country-of-origin
    flags, SBOM coverage, contract status, and CMMC control impact.
    Maps to SR.1.002.
    """
    vendor = next((v for v in _scrm.vendors if v.vendor_id == vendor_id), None)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor '{vendor_id}' not found.")

    foreign_adversary = {"China", "Russia", "North Korea", "Iran"}
    adversary_exposure = list(set(vendor.countries_of_origin) & foreign_adversary)

    risk_flags = []
    if adversary_exposure:
        risk_flags.append(
            f"Country-of-origin risk: {', '.join(adversary_exposure)}"
        )
    if vendor.risk_score >= 0.70:
        risk_flags.append("Risk score ≥ 0.70 — escalated review required.")
    if not vendor.has_sbom:
        risk_flags.append("No SBOM — software provenance unverified.")
    if not vendor.has_disposal_procedure:
        risk_flags.append("No disposal procedure — SR.2.111 gap.")
    if vendor.status == VendorStatus.SUSPENDED:
        risk_flags.append("Vendor is SUSPENDED — access should be revoked.")
    if vendor.contract_expires and vendor.contract_expires < datetime.now(UTC):
        risk_flags.append("Contract expired — remediate immediately.")

    cmmc_impact = {
        "SR.1.001": "Vendor is part of SCRM process inventory.",
        "SR.1.002": f"Risk score: {vendor.risk_score}. Flags: {risk_flags or ['None']}.",
        "SR.2.070": (
            "Contract active." if vendor.contract_expires and vendor.contract_expires > datetime.now(UTC)
            else "Contract expired or unknown."
        ),
        "SR.2.111": (
            "Disposal procedure documented."
            if vendor.has_disposal_procedure
            else "No disposal procedure — gap for SR.2.111."
        ),
    }

    return {
        "vendor_id": vendor.vendor_id,
        "name": vendor.name,
        "tier": vendor.tier.value,
        "status": vendor.status.value,
        "risk_score": vendor.risk_score,
        "cui_access": vendor.cui_access,
        "countries_of_origin": vendor.countries_of_origin,
        "adversary_country_exposure": adversary_exposure,
        "has_sbom": vendor.has_sbom,
        "has_disposal_procedure": vendor.has_disposal_procedure,
        "risk_flags": risk_flags,
        "cmmc_control_impact": cmmc_impact,
        "products": vendor.products,
        "notes": vendor.notes,
    }


@router.get("/disposal-records", summary="List component disposal records (SR.2.111)")
async def list_disposal_records():
    """Return all hardware disposal records and flag non-compliant items."""
    compliant = sum(1 for r in _scrm.disposal_records if r["compliant"])
    non_compliant = len(_scrm.disposal_records) - compliant
    return {
        "total_records": len(_scrm.disposal_records),
        "compliant": compliant,
        "non_compliant": non_compliant,
        "records": _scrm.disposal_records,
    }
