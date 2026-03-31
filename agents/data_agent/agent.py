"""
Data Protection Agent - ZT Data Pillar
AGI Corporation 2026

Aligns with DoD ZT Data Pillar and CMMC Media Protection (MP), System and
Communications Protection (SC), and Audit & Accountability (AU) domains.
Responsibilities: CUI tagging, encryption verification, audit log coverage,
data-at-rest and data-in-transit controls.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

# CMMC controls owned by this agent (MP + relevant SC + AU)
DATA_CONTROLS = [
    "MP.1.001",
    "MP.1.002",
    "MP.2.120",
    "MP.2.121",
    "MP.3.122",
    "MP.3.123",
    "SC.1.175",
    "SC.1.176",
    "SC.3.177",
    "SC.3.187",
    "AU.2.041",
    "AU.2.042",
    "AU.2.043",
    "AU.2.044",
]


class EncryptionAlgorithm(str, Enum):
    AES_256 = "AES-256"
    AES_128 = "AES-128"
    NONE = "none"
    UNKNOWN = "unknown"


@dataclass
class DataStoreRecord:
    store_id: str
    name: str
    data_classification: str  # CUI / public / internal
    encryption_at_rest: bool
    encryption_algorithm: EncryptionAlgorithm
    encryption_in_transit: bool
    tls_version: str  # TLS 1.2 / TLS 1.3 / none
    backup_encrypted: bool
    cui_tagged: bool
    retention_days: int
    location: str  # on-prem / cloud / hybrid


@dataclass
class DataAssessmentResult:
    control_id: str
    status: str
    confidence: float
    findings: List[str]
    evidence_id: str
    remediation: List[str]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DataProtectionAgent:
    """
    Data Protection Agent aligned to ZT Data Pillar.
    Assesses CUI handling, encryption, media sanitization, and audit logging.
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.data_stores: List[DataStoreRecord] = []
        self.audit_sources: List[Dict[str, Any]] = []
        if mock_mode:
            self._load_mock_data()

    def _load_mock_data(self):
        """Load representative mock data stores for demo."""
        self.data_stores = [
            DataStoreRecord(
                store_id="ds001",
                name="CUI Document Repository",
                data_classification="CUI",
                encryption_at_rest=True,
                encryption_algorithm=EncryptionAlgorithm.AES_256,
                encryption_in_transit=True,
                tls_version="TLS 1.3",
                backup_encrypted=True,
                cui_tagged=True,
                retention_days=1095,
                location="cloud",
            ),
            DataStoreRecord(
                store_id="ds002",
                name="Engineering Design DB",
                data_classification="CUI",
                encryption_at_rest=True,
                encryption_algorithm=EncryptionAlgorithm.AES_128,
                encryption_in_transit=True,
                tls_version="TLS 1.2",
                backup_encrypted=False,
                cui_tagged=False,
                retention_days=730,
                location="on-prem",
            ),
            DataStoreRecord(
                store_id="ds003",
                name="Internal HR System",
                data_classification="internal",
                encryption_at_rest=False,
                encryption_algorithm=EncryptionAlgorithm.NONE,
                encryption_in_transit=False,
                tls_version="none",
                backup_encrypted=False,
                cui_tagged=False,
                retention_days=365,
                location="on-prem",
            ),
            DataStoreRecord(
                store_id="ds004",
                name="Public Website Cache",
                data_classification="public",
                encryption_at_rest=False,
                encryption_algorithm=EncryptionAlgorithm.NONE,
                encryption_in_transit=True,
                tls_version="TLS 1.3",
                backup_encrypted=False,
                cui_tagged=False,
                retention_days=30,
                location="cloud",
            ),
        ]
        self.audit_sources = [
            {"name": "SIEM Platform", "coverage": "partial", "retention_days": 90},
            {"name": "Cloud Audit Logs", "coverage": "full", "retention_days": 365},
            {"name": "OS Audit Daemon", "coverage": "partial", "retention_days": 30},
            {"name": "Application Logs", "coverage": "full", "retention_days": 180},
        ]

    def check_encryption_at_rest(self) -> DataAssessmentResult:
        """Assess SC.3.177 - FIPS-validated encryption of CUI at rest."""
        cui_stores = [
            s for s in self.data_stores if s.data_classification == "CUI"
        ]
        encrypted = [s for s in cui_stores if s.encryption_at_rest]
        fips_approved = [
            s
            for s in encrypted
            if s.encryption_algorithm == EncryptionAlgorithm.AES_256
        ]
        backups_encrypted = [s for s in cui_stores if s.backup_encrypted]

        findings = []
        remediation = []

        if len(encrypted) < len(cui_stores):
            missing = [s.name for s in cui_stores if not s.encryption_at_rest]
            findings.append(
                f"CUI stores without encryption at rest: {missing}"
            )
            remediation.append(
                "Enable AES-256 encryption at rest for all CUI data stores immediately"
            )
        if len(fips_approved) < len(encrypted):
            weak = [
                s.name
                for s in encrypted
                if s.encryption_algorithm != EncryptionAlgorithm.AES_256
            ]
            findings.append(f"Non-FIPS-approved algorithms in use: {weak}")
            remediation.append(
                "Migrate to AES-256 (FIPS 140-2 validated) for all CUI encryption"
            )
        if len(backups_encrypted) < len(cui_stores):
            unenc_backups = [s.name for s in cui_stores if not s.backup_encrypted]
            findings.append(f"Backups not encrypted for CUI stores: {unenc_backups}")
            remediation.append("Enable encrypted backups for all CUI data stores")

        confidence = (
            (len(fips_approved) / len(cui_stores)) * 0.6
            + (len(backups_encrypted) / len(cui_stores)) * 0.4
            if cui_stores
            else 1.0
        )
        status = (
            "implemented"
            if confidence >= 0.95
            else (
                "partially_implemented" if confidence >= 0.6 else "not_implemented"
            )
        )

        return DataAssessmentResult(
            control_id="SC.3.177",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_encryption_in_transit(self) -> DataAssessmentResult:
        """Assess SC.1.175 / SC.1.176 - CUI protection during transmission."""
        cui_stores = [
            s for s in self.data_stores if s.data_classification == "CUI"
        ]
        tls_covered = [s for s in cui_stores if s.encryption_in_transit]
        tls_12_plus = [
            s
            for s in tls_covered
            if s.tls_version in ("TLS 1.2", "TLS 1.3")
        ]

        findings = []
        remediation = []

        if len(tls_covered) < len(cui_stores):
            missing = [s.name for s in cui_stores if not s.encryption_in_transit]
            findings.append(
                f"CUI transmitted without TLS protection: {missing}"
            )
            remediation.append(
                "Enforce TLS 1.2+ on all data channels carrying CUI"
            )
        if len(tls_12_plus) < len(tls_covered):
            outdated = [
                s.name
                for s in tls_covered
                if s.tls_version not in ("TLS 1.2", "TLS 1.3")
            ]
            findings.append(f"Outdated TLS versions detected: {outdated}")
            remediation.append(
                "Upgrade to TLS 1.2 minimum; disable TLS 1.0/1.1 and SSLv3"
            )

        confidence = (
            len(tls_12_plus) / len(cui_stores) if cui_stores else 1.0
        )
        status = (
            "implemented"
            if confidence >= 0.95
            else (
                "partially_implemented" if confidence >= 0.6 else "not_implemented"
            )
        )

        return DataAssessmentResult(
            control_id="SC.1.175",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_cui_handling(self) -> DataAssessmentResult:
        """Assess MP.1.001 / MP.2.120 - CUI marking and media protection."""
        cui_stores = [
            s for s in self.data_stores if s.data_classification == "CUI"
        ]
        tagged = [s for s in cui_stores if s.cui_tagged]
        retention_ok = [
            s for s in cui_stores if s.retention_days >= 1095
        ]  # 3 years

        findings = []
        remediation = []

        if len(tagged) < len(cui_stores):
            untagged = [s.name for s in cui_stores if not s.cui_tagged]
            findings.append(f"CUI stores missing classification marking: {untagged}")
            remediation.append(
                "Apply CUI banner/footer markings per CUI Registry; update DLP policy"
            )
        if len(retention_ok) < len(cui_stores):
            short_ret = [
                s.name for s in cui_stores if s.retention_days < 1095
            ]
            findings.append(
                f"CUI retention period below 3-year DoD requirement: {short_ret}"
            )
            remediation.append(
                "Update retention policies to meet DoD minimum 3-year CUI retention"
            )

        confidence = (
            0.6 * (len(tagged) / len(cui_stores))
            + 0.4 * (len(retention_ok) / len(cui_stores))
            if cui_stores
            else 1.0
        )
        status = (
            "implemented"
            if confidence >= 0.9
            else (
                "partially_implemented" if confidence >= 0.5 else "not_implemented"
            )
        )

        return DataAssessmentResult(
            control_id="MP.1.001",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_audit_logging(self) -> DataAssessmentResult:
        """Assess AU.2.041 / AU.2.042 - Audit log creation and protection."""
        full_coverage = [
            s for s in self.audit_sources if s["coverage"] == "full"
        ]
        min_retention = [
            s for s in self.audit_sources if s["retention_days"] >= 90
        ]

        findings = []
        remediation = []

        coverage_ratio = (
            len(full_coverage) / len(self.audit_sources)
            if self.audit_sources
            else 0
        )
        retention_ratio = (
            len(min_retention) / len(self.audit_sources)
            if self.audit_sources
            else 0
        )

        if coverage_ratio < 1.0:
            partial = [
                s["name"]
                for s in self.audit_sources
                if s["coverage"] != "full"
            ]
            findings.append(f"Incomplete audit coverage on: {partial}")
            remediation.append(
                "Extend SIEM collection to cover all privileged sessions and CUI access"
            )
        if retention_ratio < 1.0:
            short = [
                s["name"]
                for s in self.audit_sources
                if s["retention_days"] < 90
            ]
            findings.append(f"Audit log retention below 90 days: {short}")
            remediation.append(
                "Configure log retention to minimum 90 days online, 1 year archived"
            )

        confidence = 0.6 * coverage_ratio + 0.4 * retention_ratio
        status = (
            "implemented"
            if confidence >= 0.9
            else (
                "partially_implemented" if confidence >= 0.5 else "not_implemented"
            )
        )

        return DataAssessmentResult(
            control_id="AU.2.041",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all Data Protection assessments and return evidence-ready results."""
        assessments = [
            self.check_encryption_at_rest(),
            self.check_encryption_in_transit(),
            self.check_cui_handling(),
            self.check_audit_logging(),
        ]
        results = []
        for a in assessments:
            results.append(
                {
                    "control_id": a.control_id,
                    "zt_pillar": "Data",
                    "status": a.status,
                    "confidence": a.confidence,
                    "findings": a.findings,
                    "remediation": a.remediation,
                    "evidence_id": a.evidence_id,
                    "assessed_at": a.assessed_at.isoformat(),
                    "owner_agent": "data_protection",
                }
            )

        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="data_protection",
            trigger=trigger,
            scope="Data Pillar",
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
_data_agent = DataProtectionAgent(mock_mode=True)


@router.get("/assess", summary="Run full Data Protection assessment (ZT Data Pillar)")
async def run_data_assessment(db: AsyncSession = Depends(get_db)):
    """CUI encryption, transit protection, media handling, audit logging — ZT Data Pillar."""
    results = await _data_agent.run_full_assessment(db)
    return {
        "agent": "data_protection",
        "zt_pillar": "Data",
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/stores", summary="List data store inventory with protection status")
async def list_data_stores():
    """Return CUI data store inventory with encryption and classification status."""
    cui_stores = [
        s for s in _data_agent.data_stores if s.data_classification == "CUI"
    ]
    return {
        "total_stores": len(_data_agent.data_stores),
        "cui_stores": len(cui_stores),
        "encryption_at_rest_pct": (
            sum(1 for s in cui_stores if s.encryption_at_rest)
            / len(cui_stores)
            * 100
            if cui_stores
            else 0
        ),
        "encryption_in_transit_pct": (
            sum(1 for s in cui_stores if s.encryption_in_transit)
            / len(cui_stores)
            * 100
            if cui_stores
            else 0
        ),
        "stores": [
            {
                "store_id": s.store_id,
                "name": s.name,
                "classification": s.data_classification,
                "encryption_at_rest": s.encryption_at_rest,
                "encryption_algorithm": s.encryption_algorithm,
                "encryption_in_transit": s.encryption_in_transit,
                "tls_version": s.tls_version,
                "cui_tagged": s.cui_tagged,
                "location": s.location,
            }
            for s in _data_agent.data_stores
        ],
    }
