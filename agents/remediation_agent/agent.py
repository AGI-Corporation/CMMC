"""
Remediation Agent - ZT Automation & Orchestration Pillar
AGI Corporation 2026

Aligns with DoD ZT Automation & Orchestration pillar and CMMC Configuration
Management (CM), System & Info Integrity (SI), Incident Response (IR), and
Access Control (AC) domains.

Responsibilities:
- Ingest assessment findings from all specialist agents
- Map gaps to structured remediation playbooks
- Execute (or simulate) automated remediation actions
- Track remediation status and generate POA&M update entries
- Provide per-control remediation playbooks for operators

Maps to CMMC controls: CM.2.061, CM.2.062, CM.3.068, SI.1.210, SI.1.211,
                        SI.2.214, IR.2.093, IR.2.094, CA.2.157, CA.3.161
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AgentRunRecord, AssessmentRecord, get_db, get_latest_assessments

# CMMC controls owned / co-owned by the Remediation agent
REMEDIATION_CONTROLS = [
    "CM.2.061",   # Establish and maintain baseline configurations
    "CM.2.062",   # Establish and maintain a software inventory
    "CM.3.068",   # Restrict, disable, or prevent the use of nonessential programs
    "SI.1.210",   # Identify, report, and correct information and information system flaws
    "SI.1.211",   # Provide protection from malicious code
    "SI.1.212",   # Update malicious code protection mechanisms
    "SI.1.213",   # Perform periodic scans and real-time scans of files
    "SI.2.214",   # Scan for vulnerabilities in organizational systems periodically
    "IR.2.093",   # Track, document, and report incidents
    "IR.2.094",   # Test the organizational incident response capability
    "CA.2.157",   # Develop, document, and periodically update system security plans
    "CA.3.161",   # Monitor security controls on an ongoing basis
]


class RemediationStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REMEDIATED = "remediated"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"


class RemediationPriority(str, Enum):
    CRITICAL = "critical"   # Exploitable, CUI exposure risk
    HIGH = "high"           # Significant SPRS deduction
    MEDIUM = "medium"       # Compliance gap, not immediately exploitable
    LOW = "low"             # Best-practice improvement


@dataclass
class RemediationAction:
    action_id: str
    control_id: str
    title: str
    description: str
    priority: RemediationPriority
    automated: bool               # Can be auto-executed vs. requires human
    estimated_effort_hours: float
    cmmc_domains: List[str]
    zt_pillars: List[str]
    steps: List[str]
    validation_check: str         # How to verify remediation succeeded
    poam_required: bool


@dataclass
class RemediationRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    control_id: str = ""
    action_id: str = ""
    status: RemediationStatus = RemediationStatus.OPEN
    priority: RemediationPriority = RemediationPriority.MEDIUM
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: Optional[datetime] = None
    owner: str = "remediation_agent"
    notes: str = ""
    due_date: Optional[datetime] = None


class RemediationAgent:
    """
    Remediation Agent aligned to ZT Automation & Orchestration pillar.

    Ingests findings from all specialist agents, maps them to actionable
    remediation playbooks, tracks remediation progress, and feeds POA&M
    entries back to the Governance agent.
    """

    # ─── Remediation playbooks keyed by CMMC control ID ───────────────────────
    PLAYBOOKS: Dict[str, Dict[str, Any]] = {
        "CM.2.061": {
            "title": "Establish & Maintain Baseline Configurations",
            "priority": RemediationPriority.HIGH,
            "automated": True,
            "effort_hours": 8.0,
            "cmmc_domains": ["CM"],
            "zt_pillars": ["Device", "Application"],
            "steps": [
                "Export current system configuration via SCAP/CIS benchmark tooling",
                "Compare against approved baseline (stored in CMDB/Git)",
                "Flag configuration drift in ticketing system (Jira/ServiceNow)",
                "Apply Infrastructure-as-Code (Terraform/Ansible) to restore baseline",
                "Run automated compliance scan to confirm drift resolved",
                "Update baseline documentation and change record",
            ],
            "validation_check": "SCAP/CIS benchmark scan returns PASS with 0 critical deviations",
            "poam_required": False,
        },
        "CM.2.062": {
            "title": "Maintain Software Inventory (SBOM)",
            "priority": RemediationPriority.MEDIUM,
            "automated": True,
            "effort_hours": 4.0,
            "cmmc_domains": ["CM"],
            "zt_pillars": ["Application"],
            "steps": [
                "Run Syft or CycloneDX SBOM generator on all container images",
                "Ingest SBOM into software inventory CMDB",
                "Cross-reference against CVE feed (NVD/OSV)",
                "Flag unauthorized or EOL packages for removal",
                "Update pipeline to block builds with unapproved packages",
            ],
            "validation_check": "100% of deployed images have CycloneDX SBOM in CMDB",
            "poam_required": False,
        },
        "CM.3.068": {
            "title": "Restrict Nonessential Programs & Services",
            "priority": RemediationPriority.HIGH,
            "automated": False,
            "effort_hours": 16.0,
            "cmmc_domains": ["CM"],
            "zt_pillars": ["Device", "Application"],
            "steps": [
                "Enumerate all running services and listening ports on in-scope systems",
                "Cross-reference against approved application whitelist",
                "Disable or uninstall nonessential services (NIST SP 800-70 CCE)",
                "Apply host-based firewall rules to block unauthorized ports",
                "Document exceptions with business justification in SSP",
                "Schedule quarterly review of application whitelist",
            ],
            "validation_check": "Port scan returns only approved services; application whitelist 100% coverage",
            "poam_required": True,
        },
        "SI.1.210": {
            "title": "Identify, Report & Correct System Flaws",
            "priority": RemediationPriority.CRITICAL,
            "automated": True,
            "effort_hours": 6.0,
            "cmmc_domains": ["SI"],
            "zt_pillars": ["Device", "Application"],
            "steps": [
                "Run vulnerability scanner (Tenable/Qualys/OpenVAS) against all in-scope assets",
                "Triage findings by CVSS score and CUI exposure risk",
                "Apply OS and application patches within SLA: Critical ≤7d, High ≤30d",
                "Validate patch application with re-scan",
                "Log remediation actions in POA&M and close findings",
            ],
            "validation_check": "Re-scan shows 0 critical/high CVEs on CUI-touching systems",
            "poam_required": True,
        },
        "SI.1.211": {
            "title": "Deploy & Maintain Malicious Code Protection",
            "priority": RemediationPriority.CRITICAL,
            "automated": True,
            "effort_hours": 4.0,
            "cmmc_domains": ["SI"],
            "zt_pillars": ["Device"],
            "steps": [
                "Verify EDR/AV agent is deployed on all CUI-handling endpoints",
                "Confirm real-time protection is enabled and signatures are current",
                "Enable cloud-based threat intelligence feed integration",
                "Configure automated quarantine and alerting to SIEM",
                "Test quarantine workflow with EICAR test file",
            ],
            "validation_check": "EDR coverage 100% on in-scope endpoints; EICAR test quarantined within 60s",
            "poam_required": False,
        },
        "SI.1.212": {
            "title": "Update Malicious Code Protection Mechanisms",
            "priority": RemediationPriority.HIGH,
            "automated": True,
            "effort_hours": 2.0,
            "cmmc_domains": ["SI"],
            "zt_pillars": ["Device"],
            "steps": [
                "Enable automatic signature update on all EDR/AV deployments",
                "Verify update frequency meets policy (≤24h for signatures)",
                "Integrate EDR health dashboard into SIEM alert pipeline",
                "Alert on any endpoint with stale signatures (>24h)",
            ],
            "validation_check": "All endpoints show signature age <24h in EDR console",
            "poam_required": False,
        },
        "SI.1.213": {
            "title": "Perform Periodic & Real-Time Malware Scans",
            "priority": RemediationPriority.HIGH,
            "automated": True,
            "effort_hours": 3.0,
            "cmmc_domains": ["SI"],
            "zt_pillars": ["Device", "Application"],
            "steps": [
                "Enable on-access scanning for all file system operations on CUI systems",
                "Schedule weekly full-disk malware scans via EDR policy",
                "Enable email attachment scanning at gateway (O365 Defender/Proofpoint)",
                "Route scan results to SIEM for centralized alerting",
                "Review and tune exclusion lists quarterly to prevent evasion",
            ],
            "validation_check": "Scan logs show 100% on-access coverage; weekly full scan completed without errors",
            "poam_required": False,
        },
        "SI.2.214": {
            "title": "Vulnerability Scanning Program",
            "priority": RemediationPriority.CRITICAL,
            "automated": True,
            "effort_hours": 8.0,
            "cmmc_domains": ["SI"],
            "zt_pillars": ["Device", "Application", "Network"],
            "steps": [
                "Configure authenticated vulnerability scans in Tenable/Qualys for all in-scope assets",
                "Run scans on release of new CVEs and at minimum quarterly",
                "Integrate scanner results directly into POA&M workflow",
                "Apply Risk Acceptance for residual risk with ISSO/AO sign-off",
                "Publish scan metrics to CMMC dashboard (last scan date, open vulns by severity)",
            ],
            "validation_check": "Authenticated scan completed in last 30 days; all critical CVEs tracked in POA&M",
            "poam_required": True,
        },
        "IR.2.093": {
            "title": "Track, Document & Report Security Incidents",
            "priority": RemediationPriority.HIGH,
            "automated": False,
            "effort_hours": 12.0,
            "cmmc_domains": ["IR"],
            "zt_pillars": ["Visibility & Analytics", "Automation & Orchestration"],
            "steps": [
                "Verify incident tracking system (Jira/ServiceNow IR) is configured for CMMC categorization",
                "Ensure all SIEM alerts are routed to incident queue",
                "Document incident lifecycle: detection, triage, containment, eradication, recovery",
                "Submit US-CERT report within 72 hours for CUI-impacting incidents",
                "Conduct after-action review and update IR plan",
            ],
            "validation_check": "Last 3 incidents fully documented with US-CERT report numbers where applicable",
            "poam_required": False,
        },
        "IR.2.094": {
            "title": "Test Incident Response Capability",
            "priority": RemediationPriority.MEDIUM,
            "automated": False,
            "effort_hours": 24.0,
            "cmmc_domains": ["IR"],
            "zt_pillars": ["Automation & Orchestration"],
            "steps": [
                "Schedule annual IR tabletop exercise with ISSO, IR team, and system owners",
                "Design scenarios: ransomware, credential theft, supply chain compromise",
                "Execute tabletop and record findings in after-action report",
                "Update IR plan and runbooks based on exercise findings",
                "Verify communication trees and escalation contacts are current",
            ],
            "validation_check": "Annual tabletop completed; after-action report filed; IR plan updated",
            "poam_required": False,
        },
        "CA.2.157": {
            "title": "Develop & Update System Security Plan (SSP)",
            "priority": RemediationPriority.HIGH,
            "automated": False,
            "effort_hours": 40.0,
            "cmmc_domains": ["CA"],
            "zt_pillars": ["Visibility & Analytics"],
            "steps": [
                "Review SSP for currency (last update <12 months)",
                "Update system boundary diagram and data flow diagrams",
                "Verify all CMMC Level 2 controls are addressed in SSP",
                "Obtain ISSO and AO signatures",
                "Store in version-controlled document management system",
                "Schedule annual SSP review and update cycle",
            ],
            "validation_check": "SSP last-updated date <12 months; all 110 controls addressed; AO signature on file",
            "poam_required": False,
        },
        "CA.3.161": {
            "title": "Ongoing Security Control Monitoring",
            "priority": RemediationPriority.MEDIUM,
            "automated": True,
            "effort_hours": 16.0,
            "cmmc_domains": ["CA"],
            "zt_pillars": ["Visibility & Analytics", "Automation & Orchestration"],
            "steps": [
                "Enable continuous compliance scanning via this CMMC agent platform",
                "Configure automated SPRS score computation on daily schedule",
                "Integrate ZT pillar scorecard into executive security dashboard",
                "Establish thresholds for automatic alerts on score degradation",
                "Define and document the Ongoing Authorization (OA) process",
                "Schedule monthly control effectiveness reviews with ISSO",
            ],
            "validation_check": "Daily automated scans active; SPRS score tracked; executive dashboard populated",
            "poam_required": False,
        },
    }

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.remediation_records: List[RemediationRecord] = []
        if mock_mode:
            self._load_mock_records()

    def _load_mock_records(self):
        """Seed representative remediation records for demo."""
        seed_data = [
            ("SI.2.214", RemediationStatus.IN_PROGRESS, RemediationPriority.CRITICAL, 14),
            ("CM.3.068", RemediationStatus.OPEN, RemediationPriority.HIGH, 30),
            ("IR.2.094", RemediationStatus.OPEN, RemediationPriority.MEDIUM, 60),
            ("CA.2.157", RemediationStatus.REMEDIATED, RemediationPriority.HIGH, -5),
            ("SI.1.210", RemediationStatus.IN_PROGRESS, RemediationPriority.CRITICAL, 7),
        ]
        now = datetime.now(UTC)
        for ctrl, status, priority, due_offset in seed_data:
            pb = self.PLAYBOOKS.get(ctrl, {})
            rec = RemediationRecord(
                control_id=ctrl,
                action_id=str(uuid.uuid4()),
                status=status,
                priority=priority,
                opened_at=now - timedelta(days=abs(due_offset) + 5),
                updated_at=now,
                closed_at=now if status == RemediationStatus.REMEDIATED else None,
                due_date=now + timedelta(days=due_offset),
                notes=f"Auto-opened by remediation agent. Playbook: {pb.get('title', '')}",
            )
            self.remediation_records.append(rec)

    # ─── Assessment methods ────────────────────────────────────────────────────

    def assess_configuration_management(self) -> List[Dict[str, Any]]:
        """Evaluate CM.2.061, CM.2.062, CM.3.068 remediation posture."""
        results = []
        cm_controls = ["CM.2.061", "CM.2.062", "CM.3.068"]
        open_records = {
            r.control_id: r
            for r in self.remediation_records
            if r.control_id in cm_controls and r.status != RemediationStatus.REMEDIATED
        }

        for cid in cm_controls:
            pb = self.PLAYBOOKS[cid]
            rec = open_records.get(cid)
            has_gap = rec is not None
            confidence = 0.5 if has_gap else 0.95
            status = "partially_implemented" if has_gap else "implemented"
            findings = [f"Open remediation item for {cid}: {rec.status.value}"] if rec else []
            results.append({
                "control_id": cid,
                "status": status,
                "confidence": confidence,
                "findings": findings,
                "remediation": pb["steps"][:3] if has_gap else [],
                "evidence_id": str(uuid.uuid4()),
                "owner_agent": "remediation",
            })
        return results

    def assess_system_integrity(self) -> List[Dict[str, Any]]:
        """Evaluate SI.1.210 – SI.2.214 remediation posture."""
        results = []
        si_controls = ["SI.1.210", "SI.1.211", "SI.1.212", "SI.1.213", "SI.2.214"]
        open_records = {
            r.control_id: r
            for r in self.remediation_records
            if r.control_id in si_controls and r.status != RemediationStatus.REMEDIATED
        }

        for cid in si_controls:
            pb = self.PLAYBOOKS[cid]
            rec = open_records.get(cid)
            has_gap = rec is not None
            if has_gap and rec.priority == RemediationPriority.CRITICAL:
                confidence = 0.35
                status = "not_implemented"
            elif has_gap:
                confidence = 0.55
                status = "partially_implemented"
            else:
                confidence = 0.92
                status = "implemented"
            findings = [f"Open remediation: {rec.status.value} (priority={rec.priority.value})"] if rec else []
            results.append({
                "control_id": cid,
                "status": status,
                "confidence": confidence,
                "findings": findings,
                "remediation": pb["steps"][:3] if has_gap else [],
                "evidence_id": str(uuid.uuid4()),
                "owner_agent": "remediation",
            })
        return results

    def assess_incident_response(self) -> List[Dict[str, Any]]:
        """Evaluate IR.2.093, IR.2.094 remediation posture."""
        results = []
        ir_controls = ["IR.2.093", "IR.2.094"]
        open_records = {
            r.control_id: r
            for r in self.remediation_records
            if r.control_id in ir_controls and r.status != RemediationStatus.REMEDIATED
        }

        for cid in ir_controls:
            pb = self.PLAYBOOKS[cid]
            rec = open_records.get(cid)
            has_gap = rec is not None
            confidence = 0.6 if has_gap else 0.9
            status = "partially_implemented" if has_gap else "implemented"
            findings = [f"IR remediation open: {rec.status.value}"] if rec else []
            results.append({
                "control_id": cid,
                "status": status,
                "confidence": confidence,
                "findings": findings,
                "remediation": pb["steps"][:3] if has_gap else [],
                "evidence_id": str(uuid.uuid4()),
                "owner_agent": "remediation",
            })
        return results

    def assess_continuous_monitoring(self) -> List[Dict[str, Any]]:
        """Evaluate CA.2.157, CA.3.161 remediation posture."""
        results = []
        ca_controls = ["CA.2.157", "CA.3.161"]
        open_records = {
            r.control_id: r
            for r in self.remediation_records
            if r.control_id in ca_controls and r.status != RemediationStatus.REMEDIATED
        }

        for cid in ca_controls:
            pb = self.PLAYBOOKS[cid]
            rec = open_records.get(cid)
            has_gap = rec is not None
            confidence = 0.65 if has_gap else 0.88
            status = "partially_implemented" if has_gap else "implemented"
            findings = [f"CA remediation open: {rec.status.value}"] if rec else []
            results.append({
                "control_id": cid,
                "status": status,
                "confidence": confidence,
                "findings": findings,
                "remediation": pb["steps"][:3] if has_gap else [],
                "evidence_id": str(uuid.uuid4()),
                "owner_agent": "remediation",
            })
        return results

    async def run_full_assessment(
        self, db: AsyncSession, trigger: str = "manual"
    ) -> List[Dict[str, Any]]:
        """Run all Remediation assessments and persist an agent run record."""
        all_results: List[Dict[str, Any]] = []
        all_results.extend(self.assess_configuration_management())
        all_results.extend(self.assess_system_integrity())
        all_results.extend(self.assess_incident_response())
        all_results.extend(self.assess_continuous_monitoring())

        assessed_at = datetime.now(UTC).isoformat()
        for r in all_results:
            r.setdefault("zt_pillar", "Automation & Orchestration")
            r["assessed_at"] = assessed_at

        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="remediation",
            trigger=trigger,
            scope="Remediation Pillar",
            controls_evaluated=[r["control_id"] for r in all_results],
            findings={"results": all_results},
            status="completed",
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(record)
        await db.commit()
        return all_results

    # ─── Remediation execution helpers ────────────────────────────────────────

    def execute_remediation(self, control_id: str) -> Dict[str, Any]:
        """
        Simulate executing the remediation playbook for a control.
        In production this would call Ansible, Terraform, or ticketing APIs.
        """
        pb = self.PLAYBOOKS.get(control_id)
        if not pb:
            return {"error": f"No playbook found for control {control_id}"}

        # Update or create a remediation record
        existing = next(
            (r for r in self.remediation_records if r.control_id == control_id
             and r.status in (RemediationStatus.OPEN, RemediationStatus.IN_PROGRESS)),
            None,
        )
        if existing:
            existing.status = RemediationStatus.IN_PROGRESS
            existing.updated_at = datetime.now(UTC)
            record_id = existing.record_id
        else:
            new_rec = RemediationRecord(
                control_id=control_id,
                action_id=str(uuid.uuid4()),
                status=RemediationStatus.IN_PROGRESS,
                priority=pb["priority"],
                due_date=datetime.now(UTC) + timedelta(days=30),
                notes=f"Remediation triggered via API for {control_id}",
            )
            self.remediation_records.append(new_rec)
            record_id = new_rec.record_id

        return {
            "record_id": record_id,
            "control_id": control_id,
            "playbook_title": pb["title"],
            "status": RemediationStatus.IN_PROGRESS,
            "automated": pb["automated"],
            "steps_initiated": pb["steps"],
            "estimated_effort_hours": pb["effort_hours"],
            "validation_check": pb["validation_check"],
            "triggered_at": datetime.now(UTC).isoformat(),
        }

    def get_remediation_status(self) -> Dict[str, Any]:
        """Aggregate remediation pipeline status across all records."""
        total = len(self.remediation_records)
        by_status: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        overdue: List[Dict] = []
        now = datetime.now(UTC)

        for rec in self.remediation_records:
            by_status[rec.status.value] = by_status.get(rec.status.value, 0) + 1
            by_priority[rec.priority.value] = by_priority.get(rec.priority.value, 0) + 1
            if (
                rec.due_date
                and rec.due_date < now
                and rec.status not in (RemediationStatus.REMEDIATED, RemediationStatus.ACCEPTED_RISK)
            ):
                overdue.append({
                    "control_id": rec.control_id,
                    "priority": rec.priority.value,
                    "due_date": rec.due_date.isoformat(),
                    "days_overdue": (now - rec.due_date).days,
                })

        return {
            "total_items": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue_items": overdue,
            "overdue_count": len(overdue),
            "remediated_count": by_status.get(RemediationStatus.REMEDIATED, 0),
            "open_count": by_status.get(RemediationStatus.OPEN, 0),
            "in_progress_count": by_status.get(RemediationStatus.IN_PROGRESS, 0),
        }

    def ingest_assessment_findings(
        self, findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Accept cross-agent assessment results and open remediation records
        for any control with status != 'implemented'.
        Returns list of newly created remediation records.
        """
        created = []
        existing_open = {
            r.control_id
            for r in self.remediation_records
            if r.status in (RemediationStatus.OPEN, RemediationStatus.IN_PROGRESS)
        }

        for finding in findings:
            ctrl = finding.get("control_id", "")
            status = finding.get("status", "")
            if status in ("not_implemented", "partially_implemented") and ctrl not in existing_open:
                pb = self.PLAYBOOKS.get(ctrl)
                priority = pb["priority"] if pb else RemediationPriority.MEDIUM
                new_rec = RemediationRecord(
                    control_id=ctrl,
                    action_id=str(uuid.uuid4()),
                    status=RemediationStatus.OPEN,
                    priority=priority,
                    due_date=datetime.now(UTC) + timedelta(days=30),
                    notes=f"Auto-opened from agent finding: {finding.get('findings', [])}",
                )
                self.remediation_records.append(new_rec)
                created.append({
                    "record_id": new_rec.record_id,
                    "control_id": ctrl,
                    "priority": priority.value,
                    "status": RemediationStatus.OPEN,
                })
        return created


# ─── FastAPI endpoint integration ──────────────────────────────────────────────

router = APIRouter()
_remediation = RemediationAgent(mock_mode=True)


@router.get(
    "/assess",
    summary="Run full Remediation posture assessment (ZT Automation & Orchestration)",
)
async def run_remediation_assessment(db: AsyncSession = Depends(get_db)):
    """
    Assess CM, SI, IR, and CA control implementation status through the lens of
    the remediation pipeline. Maps to DoD ZT Automation & Orchestration pillar.
    """
    results = await _remediation.run_full_assessment(db)
    return {
        "agent": "remediation",
        "zt_pillar": "Automation & Orchestration",
        "assessments": results,
        "controls_evaluated": [r["control_id"] for r in results],
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/status", summary="Get remediation pipeline status and metrics")
async def get_remediation_status():
    """Return aggregate remediation status: open/in-progress/remediated counts, overdue items."""
    return _remediation.get_remediation_status()


@router.get(
    "/playbook/{control_id}",
    summary="Get remediation playbook for a specific CMMC control",
)
async def get_playbook(control_id: str):
    """
    Return the structured remediation playbook for a given CMMC control ID.
    Includes step-by-step instructions, estimated effort, and validation check.
    """
    pb = _remediation.PLAYBOOKS.get(control_id)
    if not pb:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"No remediation playbook found for control '{control_id}'. "
                   f"Available controls: {list(_remediation.PLAYBOOKS.keys())}",
        )
    return {
        "control_id": control_id,
        "playbook": {
            "title": pb["title"],
            "priority": pb["priority"],
            "automated": pb["automated"],
            "estimated_effort_hours": pb["effort_hours"],
            "cmmc_domains": pb["cmmc_domains"],
            "zt_pillars": pb["zt_pillars"],
            "steps": pb["steps"],
            "validation_check": pb["validation_check"],
            "poam_required": pb["poam_required"],
        },
    }


@router.post(
    "/remediate/{control_id}",
    summary="Execute remediation playbook for a CMMC control",
)
async def execute_remediation(control_id: str):
    """
    Trigger the remediation playbook for the specified CMMC control.
    Updates the remediation record to IN_PROGRESS and returns initiated steps.
    """
    result = _remediation.execute_remediation(control_id)
    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post(
    "/ingest",
    summary="Ingest cross-agent assessment findings and open remediation items",
)
async def ingest_findings(
    findings: List[Dict[str, Any]] = Body(...),
):
    """
    Accept a list of assessment findings from specialist agents and automatically
    open remediation records for any control not fully implemented.
    """
    created = _remediation.ingest_assessment_findings(findings)
    return {
        "ingested": len(findings),
        "new_remediation_items": len(created),
        "items": created,
    }
