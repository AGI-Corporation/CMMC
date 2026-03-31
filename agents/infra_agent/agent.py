"""
Infrastructure Agent - ZT Device & Network Pillars
AGI Corporation 2026

Aligns with DoD ZT Device and Network Pillars, CMMC Configuration Management
(CM), Maintenance (MA), Physical Protection (PE), and System Communications
Protection (SC) domains. Fulcrum LOE 2 - Network security.

Responsibilities: network segmentation, configuration baselines,
vulnerability scanning, physical access controls, maintenance hygiene.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, get_db

INFRA_CONTROLS = [
    "CM.2.061",
    "CM.2.062",
    "CM.2.064",
    "CM.3.068",
    "SC.1.175",
    "SC.1.176",
    "SC.3.177",
    "SC.3.187",
    "MA.2.111",
    "MA.2.112",
    "MA.2.113",
    "PE.1.131",
    "PE.1.132",
    "PE.2.135",
    "PE.3.136",
]


class NetworkZone(str, Enum):
    CUI_ENCLAVE = "cui_enclave"
    CORPORATE = "corporate"
    DMZ = "dmz"
    INTERNET = "internet"
    MANAGEMENT = "management"


@dataclass
class NetworkSegment:
    segment_id: str
    name: str
    zone: NetworkZone
    vlan_id: int
    firewall_enforced: bool
    micro_segmentation: bool
    cui_traffic: bool
    inter_zone_acl: bool
    ids_ips_enabled: bool


@dataclass
class DeviceRecord:
    device_id: str
    hostname: str
    device_type: str  # server / workstation / network / iot
    os: str
    os_patch_level: str
    last_patched: datetime
    configuration_baseline: str  # applied / partial / none
    stig_compliant: bool
    fips_enabled: bool
    endpoint_detection: bool
    zone: NetworkZone


@dataclass
class InfraAssessmentResult:
    control_id: str
    status: str
    confidence: float
    findings: List[str]
    evidence_id: str
    remediation: List[str]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InfrastructureAgent:
    """
    Infrastructure Agent aligned to ZT Device and Network Pillars.
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.segments: List[NetworkSegment] = []
        self.devices: List[DeviceRecord] = []
        if mock_mode:
            self._load_mock_infra()

    def _load_mock_infra(self):
        self.segments = [
            NetworkSegment(
                segment_id="seg001",
                name="CUI Enclave",
                zone=NetworkZone.CUI_ENCLAVE,
                vlan_id=100,
                firewall_enforced=True,
                micro_segmentation=True,
                cui_traffic=True,
                inter_zone_acl=True,
                ids_ips_enabled=True,
            ),
            NetworkSegment(
                segment_id="seg002",
                name="Corporate LAN",
                zone=NetworkZone.CORPORATE,
                vlan_id=200,
                firewall_enforced=True,
                micro_segmentation=False,
                cui_traffic=False,
                inter_zone_acl=True,
                ids_ips_enabled=True,
            ),
            NetworkSegment(
                segment_id="seg003",
                name="Guest / DMZ",
                zone=NetworkZone.DMZ,
                vlan_id=300,
                firewall_enforced=True,
                micro_segmentation=False,
                cui_traffic=False,
                inter_zone_acl=True,
                ids_ips_enabled=False,
            ),
            NetworkSegment(
                segment_id="seg004",
                name="Management Network",
                zone=NetworkZone.MANAGEMENT,
                vlan_id=400,
                firewall_enforced=True,
                micro_segmentation=True,
                cui_traffic=False,
                inter_zone_acl=True,
                ids_ips_enabled=True,
            ),
        ]
        now = datetime.now(UTC)
        self.devices = [
            DeviceRecord(
                device_id="dev001",
                hostname="cui-app-server-01",
                device_type="server",
                os="RHEL 9",
                os_patch_level="2024-Q4",
                last_patched=now - timedelta(days=15),
                configuration_baseline="applied",
                stig_compliant=True,
                fips_enabled=True,
                endpoint_detection=True,
                zone=NetworkZone.CUI_ENCLAVE,
            ),
            DeviceRecord(
                device_id="dev002",
                hostname="corp-workstation-42",
                device_type="workstation",
                os="Windows 11",
                os_patch_level="2024-Q3",
                last_patched=now - timedelta(days=45),
                configuration_baseline="partial",
                stig_compliant=False,
                fips_enabled=False,
                endpoint_detection=True,
                zone=NetworkZone.CORPORATE,
            ),
            DeviceRecord(
                device_id="dev003",
                hostname="legacy-build-server",
                device_type="server",
                os="Ubuntu 20.04",
                os_patch_level="2023-Q2",
                last_patched=now - timedelta(days=300),
                configuration_baseline="none",
                stig_compliant=False,
                fips_enabled=False,
                endpoint_detection=False,
                zone=NetworkZone.CORPORATE,
            ),
            DeviceRecord(
                device_id="dev004",
                hostname="network-fw-01",
                device_type="network",
                os="Palo Alto PAN-OS",
                os_patch_level="2024-Q4",
                last_patched=now - timedelta(days=10),
                configuration_baseline="applied",
                stig_compliant=True,
                fips_enabled=True,
                endpoint_detection=False,
                zone=NetworkZone.MANAGEMENT,
            ),
        ]

    def check_network_segmentation(self) -> InfraAssessmentResult:
        """Assess SC.3.177 / SC.3.187 - Network segmentation and CUI enclave isolation."""
        cui_segments = [s for s in self.segments if s.cui_traffic]
        seg_with_fw = [s for s in cui_segments if s.firewall_enforced]
        micro_seg = [s for s in cui_segments if s.micro_segmentation]
        ids_covered = [s for s in cui_segments if s.ids_ips_enabled]

        findings = []
        remediation = []

        if len(seg_with_fw) < len(cui_segments):
            missing = [s.name for s in cui_segments if not s.firewall_enforced]
            findings.append(f"CUI segments without firewall enforcement: {missing}")
            remediation.append(
                "Deploy NGFW rules to enforce strict perimeter around CUI enclaves"
            )
        if len(micro_seg) < len(cui_segments):
            lacking = [s.name for s in cui_segments if not s.micro_segmentation]
            findings.append(f"CUI segments lacking micro-segmentation: {lacking}")
            remediation.append(
                "Implement software-defined networking (SDN) micro-segmentation "
                "for lateral movement prevention within CUI zones"
            )
        if len(ids_covered) < len(cui_segments):
            unmonitored = [s.name for s in cui_segments if not s.ids_ips_enabled]
            findings.append(f"CUI segments without IDS/IPS coverage: {unmonitored}")
            remediation.append(
                "Deploy network IDS/IPS sensors on all CUI segment boundaries"
            )

        confidence = (
            (
                0.4 * (len(seg_with_fw) / len(cui_segments))
                + 0.35 * (len(micro_seg) / len(cui_segments))
                + 0.25 * (len(ids_covered) / len(cui_segments))
            )
            if cui_segments
            else 1.0
        )
        status = (
            "implemented"
            if confidence >= 0.9
            else (
                "partially_implemented" if confidence >= 0.6 else "not_implemented"
            )
        )

        return InfraAssessmentResult(
            control_id="SC.3.177",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_configuration_baselines(self) -> InfraAssessmentResult:
        """Assess CM.2.061 / CM.2.062 - Configuration baselines and STIG compliance."""
        servers = [d for d in self.devices if d.device_type == "server"]
        workstations = [d for d in self.devices if d.device_type == "workstation"]
        managed = servers + workstations

        baseline_applied = [
            d for d in managed if d.configuration_baseline == "applied"
        ]
        stig_ok = [d for d in managed if d.stig_compliant]
        fips_ok = [
            d for d in managed if d.fips_enabled and d.zone == NetworkZone.CUI_ENCLAVE
        ]
        cui_devices = [
            d for d in managed if d.zone == NetworkZone.CUI_ENCLAVE
        ]

        findings = []
        remediation = []

        if len(baseline_applied) < len(managed):
            not_baselined = [
                d.hostname for d in managed if d.configuration_baseline != "applied"
            ]
            findings.append(f"Devices without approved configuration baseline: {not_baselined}")
            remediation.append(
                "Apply DoD STIG-derived baseline to all managed endpoints via DSC/Ansible"
            )
        if len(stig_ok) < len(managed):
            non_stig = [d.hostname for d in managed if not d.stig_compliant]
            findings.append(f"Devices not meeting STIG compliance: {non_stig}")
            remediation.append(
                "Remediate STIG findings using SCAP/SCC tooling; target Cat I findings first"
            )
        if cui_devices and len(fips_ok) < len(cui_devices):
            no_fips = [
                d.hostname
                for d in cui_devices
                if not d.fips_enabled
            ]
            findings.append(f"CUI-zone devices without FIPS mode enabled: {no_fips}")
            remediation.append(
                "Enable FIPS 140-2 mode on OS and cryptographic modules for CUI hosts"
            )

        base_ratio = len(baseline_applied) / len(managed) if managed else 1.0
        stig_ratio = len(stig_ok) / len(managed) if managed else 1.0
        fips_ratio = (
            len(fips_ok) / len(cui_devices) if cui_devices else 1.0
        )
        confidence = 0.4 * base_ratio + 0.35 * stig_ratio + 0.25 * fips_ratio

        status = (
            "implemented"
            if confidence >= 0.9
            else (
                "partially_implemented" if confidence >= 0.55 else "not_implemented"
            )
        )

        return InfraAssessmentResult(
            control_id="CM.2.061",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_patch_currency(self) -> InfraAssessmentResult:
        """Assess CM.3.068 / SI.1.210 - Patch management currency."""
        now = datetime.now(UTC)
        critical_threshold = timedelta(days=30)
        standard_threshold = timedelta(days=90)

        servers = [d for d in self.devices if d.device_type == "server"]
        workstations = [d for d in self.devices if d.device_type == "workstation"]

        servers_overdue = [
            d for d in servers if (now - d.last_patched) > critical_threshold
        ]
        workstations_overdue = [
            d for d in workstations if (now - d.last_patched) > standard_threshold
        ]

        findings = []
        remediation = []

        if servers_overdue:
            names = [d.hostname for d in servers_overdue]
            findings.append(
                f"Servers overdue for patching (>30 days): {names}"
            )
            remediation.append(
                "Apply OS patches to servers within 30 days; critical patches within 72 hours"
            )
        if workstations_overdue:
            names = [d.hostname for d in workstations_overdue]
            findings.append(
                f"Workstations overdue for patching (>90 days): {names}"
            )
            remediation.append(
                "Enforce patch policy via WSUS/SCCM; deploy missing patches to endpoints"
            )

        managed = servers + workstations
        overdue = servers_overdue + workstations_overdue
        confidence = (
            max(0.0, 1.0 - len(overdue) / max(len(managed), 1))
            if managed
            else 1.0
        )
        status = (
            "implemented"
            if confidence >= 0.9
            else (
                "partially_implemented" if confidence >= 0.6 else "not_implemented"
            )
        )

        return InfraAssessmentResult(
            control_id="CM.3.068",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    def check_endpoint_detection(self) -> InfraAssessmentResult:
        """Assess CM.2.064 - Endpoint protection and detection capabilities."""
        servers = [d for d in self.devices if d.device_type == "server"]
        workstations = [d for d in self.devices if d.device_type == "workstation"]
        managed = servers + workstations

        edr_covered = [d for d in managed if d.endpoint_detection]

        findings = []
        remediation = []

        if len(edr_covered) < len(managed):
            no_edr = [d.hostname for d in managed if not d.endpoint_detection]
            findings.append(f"Endpoints without EDR/AV coverage: {no_edr}")
            remediation.append(
                "Deploy approved EDR solution (CrowdStrike/Defender ATP) to all managed endpoints"
            )

        confidence = len(edr_covered) / len(managed) if managed else 1.0
        status = (
            "implemented"
            if confidence >= 0.95
            else (
                "partially_implemented" if confidence >= 0.7 else "not_implemented"
            )
        )

        return InfraAssessmentResult(
            control_id="CM.2.064",
            status=status,
            confidence=round(confidence, 2),
            findings=findings,
            evidence_id=str(uuid.uuid4()),
            remediation=remediation,
        )

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all Infrastructure assessments and return evidence-ready results."""
        assessments = [
            self.check_network_segmentation(),
            self.check_configuration_baselines(),
            self.check_patch_currency(),
            self.check_endpoint_detection(),
        ]

        # Map controls to ZT pillars
        zt_map = {
            "SC.3.177": "Network",
            "CM.2.061": "Device",
            "CM.3.068": "Device",
            "CM.2.064": "Device",
        }

        results = []
        for a in assessments:
            results.append(
                {
                    "control_id": a.control_id,
                    "zt_pillar": zt_map.get(a.control_id, "Device"),
                    "status": a.status,
                    "confidence": a.confidence,
                    "findings": a.findings,
                    "remediation": a.remediation,
                    "evidence_id": a.evidence_id,
                    "assessed_at": a.assessed_at.isoformat(),
                    "owner_agent": "infrastructure",
                }
            )

        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="infrastructure",
            trigger=trigger,
            scope="Device and Network Pillars",
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
_infra = InfrastructureAgent(mock_mode=True)


@router.get(
    "/assess",
    summary="Run full Infrastructure assessment (ZT Device & Network Pillars)",
)
async def run_infra_assessment(db: AsyncSession = Depends(get_db)):
    """Network segmentation, config baselines, patch currency, EDR — ZT Device & Network."""
    results = await _infra.run_full_assessment(db)
    return {
        "agent": "infrastructure",
        "zt_pillars": ["Device", "Network"],
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/network-topology", summary="Get network segment topology and security posture")
async def get_network_topology():
    """Return network segment inventory with segmentation and IDS/IPS status."""
    return {
        "total_segments": len(_infra.segments),
        "cui_segments": sum(1 for s in _infra.segments if s.cui_traffic),
        "micro_segmented": sum(1 for s in _infra.segments if s.micro_segmentation),
        "ids_ips_covered": sum(1 for s in _infra.segments if s.ids_ips_enabled),
        "segments": [
            {
                "segment_id": s.segment_id,
                "name": s.name,
                "zone": s.zone,
                "vlan_id": s.vlan_id,
                "firewall_enforced": s.firewall_enforced,
                "micro_segmentation": s.micro_segmentation,
                "cui_traffic": s.cui_traffic,
                "ids_ips_enabled": s.ids_ips_enabled,
            }
            for s in _infra.segments
        ],
    }


@router.get("/devices", summary="List device inventory with compliance posture")
async def list_devices():
    """Return device inventory with STIG, FIPS, and EDR coverage status."""
    return {
        "total_devices": len(_infra.devices),
        "stig_compliant_pct": (
            sum(1 for d in _infra.devices if d.stig_compliant)
            / len(_infra.devices)
            * 100
            if _infra.devices
            else 0
        ),
        "edr_coverage_pct": (
            sum(1 for d in _infra.devices if d.endpoint_detection)
            / len(_infra.devices)
            * 100
            if _infra.devices
            else 0
        ),
        "devices": [
            {
                "device_id": d.device_id,
                "hostname": d.hostname,
                "device_type": d.device_type,
                "os": d.os,
                "last_patched": d.last_patched.isoformat(),
                "configuration_baseline": d.configuration_baseline,
                "stig_compliant": d.stig_compliant,
                "fips_enabled": d.fips_enabled,
                "endpoint_detection": d.endpoint_detection,
                "zone": d.zone,
            }
            for d in _infra.devices
        ],
    }
