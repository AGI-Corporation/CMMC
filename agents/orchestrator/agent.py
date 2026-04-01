"""
CMMC Compliance Orchestrator Agent
AGI Corporation 2026

The Orchestrator is the top-level coordinator in the agent network.
It maintains the compliance knowledge graph, routes tasks to specialist
agents, aggregates evidence, and generates unified compliance scorecards.

Aligns with DoD ZT Orchestration/Automation pillar and Fulcrum LOE 3/4.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (AgentRunRecord, AssessmentRecord,
                                  ControlRecord, get_db,
                                  get_latest_assessments)


class AgentType(str, Enum):
    ICAM = "icam"              # Identity/Credential/Access Mgmt
    DATA = "data_protection"   # Data-centric security
    INFRA = "infrastructure"   # Network/micro-segmentation
    DEVSECOPS = "devsecops"    # DevSecOps/supply chain
    GOVERNANCE = "governance"  # Policy/risk/POA&M
    OPS = "operations"         # IR/SIEM/SOAR
    REMEDIATION = "remediation"  # Auto-remediation & playbooks
    SUPPLY_CHAIN = "supply_chain"  # SCRM / SR domain
    AWARENESS = "awareness"    # Awareness & Training / Personnel Security (AT/PS)
    MISTRAL = "mistral"        # AI analysis engine


class TaskTrigger(str, Enum):
    CODE_PUSH = "code_push"
    INCIDENT = "incident"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    ASSESSMENT = "assessment"


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trigger: TaskTrigger = TaskTrigger.MANUAL
    scope: str = ""  # system name or service
    required_controls: List[str] = field(default_factory=list)
    assigned_agents: List[AgentType] = field(default_factory=list)
    status: str = "pending"  # pending/running/completed/failed
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    findings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlStatus:
    """Canonical control status record - shared schema for all agents."""

    control_id: str
    zt_pillar: str
    status: str  # implemented/partial/planned/not_implemented
    confidence: float  # 0.0-1.0 ZT confidence score
    evidence_ids: List[str] = field(default_factory=list)
    owner_agent: AgentType = AgentType.GOVERNANCE
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""


class ComplianceOrchestrator:
    """
    Central orchestrator that:
    1. Decomposes compliance tasks into agent-specific sub-tasks
    2. Dispatches tasks to specialist agents and aggregates findings
    3. Computes ZT pillar maturity scores and SPRS score
    4. Generates dashboard-ready scorecards
    5. Routes incidents to OPS agent and code pushes to DevSecOps agent
    """

    # ZT Pillar -> CMMC domains mapping (DoD ZT Strategy alignment)
    ZT_DOMAIN_MAP = {
        "User": ["AC", "IA", "PS", "AT"],
        "Device": ["CM", "MA", "PE"],
        "Network": ["SC", "AC"],
        "Application": ["CM", "CA", "SI"],
        "Data": ["MP", "SC", "AU"],
        "Visibility & Analytics": ["AU", "IR", "RA"],
        "Automation & Orchestration": ["IR", "SI", "CA"],
    }

    # SPRS point deductions per control (from DoD assessment methodology)
    # Total possible score = 110 points
    SPRS_DEDUCTIONS = {
        # High value controls (5 points each)
        "AC.2.006": 5,
        "AC.2.007": 5,
        "AC.3.017": 5,
        "AC.3.018": 5,
        "IA.3.083": 5,
        "IA.3.084": 5,
        "SC.3.177": 5,
        # Medium value controls (3 points each)
        "AC.1.001": 3,
        "AC.1.002": 3,
        "IA.1.076": 3,
        "IA.1.077": 3,
        "SC.1.175": 3,
        "SC.1.176": 3,
        "SI.1.210": 3,
        "SI.1.211": 3,
        "SI.1.212": 3,
        "SI.1.213": 3,
    }

    def __init__(self):
        self.control_registry: Dict[str, ControlStatus] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.evidence_store: Dict[str, Dict] = {}
        self.agent_runs: List[Dict] = []

    def create_task(
        self,
        trigger: TaskTrigger,
        scope: str,
        required_controls: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> Task:
        """Create and route a compliance task to appropriate agents."""
        task = Task(
            trigger=trigger,
            scope=scope,
            required_controls=required_controls or [],
        )
        # Route based on trigger type
        if trigger == TaskTrigger.CODE_PUSH:
            task.assigned_agents = [
                AgentType.DEVSECOPS,
                AgentType.ICAM,
                AgentType.MISTRAL,
            ]
            task.required_controls = task.required_controls or [
                "SI.2.214",
                "CM.2.061",
                "AC.1.001",
            ]
        elif trigger == TaskTrigger.INCIDENT:
            task.assigned_agents = [AgentType.OPS, AgentType.GOVERNANCE]
            task.required_controls = task.required_controls or [
                "IR.2.092",
                "IR.2.093",
                "AU.2.041",
            ]
        elif trigger == TaskTrigger.ASSESSMENT:
            task.assigned_agents = [
                AgentType.ICAM,
                AgentType.DATA,
                AgentType.INFRA,
                AgentType.DEVSECOPS,
                AgentType.GOVERNANCE,
                AgentType.OPS,
                AgentType.REMEDIATION,
                AgentType.SUPPLY_CHAIN,
                AgentType.AWARENESS,
            ]
        elif trigger == TaskTrigger.SCHEDULE:
            task.assigned_agents = [
                AgentType.ICAM,
                AgentType.INFRA,
                AgentType.GOVERNANCE,
                AgentType.OPS,
                AgentType.AWARENESS,
            ]
        else:  # MANUAL
            task.assigned_agents = [AgentType.GOVERNANCE]

        self.task_queue.append(task)
        return task

    async def execute_task(self, task: Task, db: AsyncSession) -> Dict[str, Any]:
        """
        Dispatch a compliance task to assigned agents and aggregate findings.
        Agent imports are deferred inside the method to avoid circular imports.
        """
        from agents.awareness_agent import agent as awareness_module
        from agents.data_agent import agent as data_module
        from agents.devsecops_agent import agent as devsecops_module
        from agents.governance_agent import agent as governance_module
        from agents.icam_agent import agent as icam_module
        from agents.infra_agent import agent as infra_module
        from agents.ops_agent import agent as ops_module
        from agents.remediation_agent import agent as remediation_module
        from agents.supply_chain_agent import agent as supply_chain_module

        agent_instances = {
            AgentType.ICAM: icam_module._icam,
            AgentType.DATA: data_module._data_agent,
            AgentType.INFRA: infra_module._infra,
            AgentType.DEVSECOPS: devsecops_module._dso,
            AgentType.GOVERNANCE: governance_module._governance,
            AgentType.OPS: ops_module._ops,
            AgentType.REMEDIATION: remediation_module._remediation,
            AgentType.SUPPLY_CHAIN: supply_chain_module._scrm,
            AgentType.AWARENESS: awareness_module._awareness,
        }

        all_results: List[Dict[str, Any]] = []
        task.status = "running"

        for agent_type in task.assigned_agents:
            if agent_type == AgentType.MISTRAL:
                # Mistral is invoked on-demand per control; skip in bulk runs
                continue
            agent_obj = agent_instances.get(agent_type)
            if agent_obj is None:
                continue
            try:
                results = await agent_obj.run_full_assessment(
                    db, trigger=task.trigger.value
                )
                all_results.extend(results)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(
                    "Agent %s failed during task %s: %s",
                    agent_type.value,
                    task.id,
                    exc,
                    exc_info=True,
                )
                all_results.append(
                    {
                        "agent": agent_type.value,
                        "error": "Agent assessment failed; check server logs for details.",
                        "status": "failed",
                    }
                )

        task.findings = {"results": all_results}
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        self.completed_tasks.append(task)
        if task in self.task_queue:
            self.task_queue.remove(task)

        return task.findings

    async def compute_sprs_score(self, db: AsyncSession) -> Dict[str, Any]:
        """Compute SPRS score using methodology from assessment.py."""
        result = await db.execute(select(ControlRecord))
        controls = result.scalars().all()
        sprs = 110
        deductions_list = []
        implemented_count = not_implemented_count = 0

        assessments_map = await get_latest_assessments(db)

        for c in controls:
            cid = c.id
            assessment = assessments_map.get(cid)
            status = assessment.status if assessment else "not_started"

            if status == "implemented":
                implemented_count += 1
            elif status in ["not_implemented", "not_started", "partially_implemented"]:
                not_implemented_count += 1
                deduction = self.SPRS_DEDUCTIONS.get(cid, 1)
                sprs -= deduction
                deductions_list.append({"control_id": cid, "deduction": deduction})

        return {
            "sprs_score": max(-203, sprs),
            "max_score": 110,
            "controls_assessed": len(controls),
            "controls_implemented": implemented_count,
            "controls_not_implemented": not_implemented_count,
            "deductions": deductions_list,
        }

    async def compute_zt_scorecard(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Generate per-ZT-pillar maturity scorecard from database."""
        scorecard = []
        assessments_map = await get_latest_assessments(db)

        for pillar, domains in self.ZT_DOMAIN_MAP.items():
            query = select(ControlRecord).where(ControlRecord.domain.in_(domains))
            result = await db.execute(query)
            controls = result.scalars().all()

            if not controls:
                continue

            total = len(controls)
            implemented = 0
            partial = 0
            confidences = []

            for c in controls:
                assessment = assessments_map.get(c.id)
                if assessment:
                    status = assessment.status
                    confidences.append(assessment.confidence)
                    if status == "implemented":
                        implemented += 1
                    elif status in ("partially_implemented", "partial"):
                        # Both values appear in the DB; "partial" is a legacy alias
                        partial += 1
                else:
                    confidences.append(0.0)

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            scorecard.append(
                {
                    "pillar": pillar,
                    "total_controls": total,
                    "implemented": implemented,
                    "partial": partial,
                    "not_implemented": total - implemented - partial,
                    "maturity_pct": (
                        round((implemented + 0.5 * partial) / total * 100, 1)
                        if total > 0
                        else 0
                    ),
                    "confidence_avg": round(avg_confidence, 2),
                }
            )
        return scorecard

    async def generate_report(self, db: AsyncSession) -> Dict[str, Any]:
        """Generate a complete compliance run report."""
        sprs_data = await self.compute_sprs_score(db)
        zt_scorecard = await self.compute_zt_scorecard(db)

        runs_query = (
            select(AgentRunRecord).order_by(AgentRunRecord.created_at.desc()).limit(10)
        )
        runs_result = await db.execute(runs_query)
        runs = runs_result.scalars().all()

        return {
            "report_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "sprs_score": sprs_data["sprs_score"],
            "sprs_details": sprs_data,
            "zt_scorecard": zt_scorecard,
            "agent_runs": [
                {
                    "agent": r.agent_type,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "scope": r.scope,
                }
                for r in runs
            ],
        }


# ─── FastAPI endpoint integration ─────────────────────────────────────────────

router = APIRouter()
_orchestrator = ComplianceOrchestrator()


@router.post("/task", summary="Create and route a compliance task")
async def create_task(trigger: str, scope: str, controls: str = ""):
    """Create a new orchestrated compliance task (does not execute it)."""
    task = _orchestrator.create_task(
        trigger=TaskTrigger(trigger),
        scope=scope,
        required_controls=controls.split(",") if controls else None,
    )
    return {
        "task_id": task.id,
        "assigned_agents": task.assigned_agents,
        "required_controls": task.required_controls,
        "status": task.status,
    }


@router.post("/run", summary="Create, route, and execute a compliance task across all assigned agents")
async def run_task(
    trigger: str = "manual",
    scope: str = "full-system",
    controls: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    Create a compliance task and immediately execute it across all assigned
    specialist agents. Aggregates findings from ICAM, Data, Infra, DevSecOps,
    Governance, and OPS agents based on the trigger type.
    """
    task = _orchestrator.create_task(
        trigger=TaskTrigger(trigger),
        scope=scope,
        required_controls=controls.split(",") if controls else None,
    )
    findings = await _orchestrator.execute_task(task, db)
    return {
        "task_id": task.id,
        "trigger": trigger,
        "scope": scope,
        "assigned_agents": task.assigned_agents,
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "total_assessments": len(findings.get("results", [])),
        "findings": findings,
    }


@router.post(
    "/webhook/code-push",
    summary="Webhook: trigger DevSecOps + ICAM agent run on code push event",
)
async def webhook_code_push(
    service: str = Body(..., embed=True),
    branch: str = Body("main", embed=True),
    commit_sha: str = Body("", embed=True),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a code-push event and trigger automated DevSecOps pipeline assessment.
    Routes to DevSecOps agent (container scan, SBOM, pipeline gates) and ICAM
    agent (access control verification).
    Maps to CMMC CM.2.061, SI.2.214, AC.1.001.
    """
    scope = f"{service}@{branch}"
    task = _orchestrator.create_task(
        trigger=TaskTrigger.CODE_PUSH,
        scope=scope,
        context={"commit_sha": commit_sha},
    )
    findings = await _orchestrator.execute_task(task, db)
    return {
        "event": "code_push",
        "service": service,
        "branch": branch,
        "commit_sha": commit_sha or "unknown",
        "task_id": task.id,
        "status": task.status,
        "assessments_run": len(findings.get("results", [])),
        "findings_summary": [
            {
                "control_id": r.get("control_id"),
                "status": r.get("status"),
                "confidence": r.get("confidence"),
                "owner_agent": r.get("owner_agent"),
            }
            for r in findings.get("results", [])
            if "control_id" in r
        ],
    }


@router.post(
    "/webhook/incident",
    summary="Webhook: trigger OPS + Governance agent run on security incident",
)
async def webhook_incident(
    incident_type: str = Body(..., embed=True),
    description: str = Body(..., embed=True),
    severity: str = Body("P3", embed=True),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a security incident alert and trigger automated IR agent assessment.
    Routes to OPS agent (incident triage, SIEM coverage) and Governance agent
    (policy status, POA&M).
    Maps to CMMC IR.2.092, IR.2.093, AU.2.041.
    """
    scope = f"incident:{incident_type}"
    task = _orchestrator.create_task(
        trigger=TaskTrigger.INCIDENT,
        scope=scope,
        context={"description": description, "severity": severity},
    )
    findings = await _orchestrator.execute_task(task, db)
    return {
        "event": "incident",
        "incident_type": incident_type,
        "severity": severity,
        "task_id": task.id,
        "status": task.status,
        "assessments_run": len(findings.get("results", [])),
        "ir_controls_engaged": ["IR.2.092", "IR.2.093", "IR.2.094", "AU.2.041"],
        "findings_summary": [
            {
                "control_id": r.get("control_id"),
                "status": r.get("status"),
                "confidence": r.get("confidence"),
                "owner_agent": r.get("owner_agent"),
            }
            for r in findings.get("results", [])
            if "control_id" in r
        ],
    }


@router.get("/scorecard", summary="Get ZT pillar compliance scorecard")
async def get_scorecard(db: AsyncSession = Depends(get_db)):
    """Return current ZT pillar maturity scorecard."""
    return {
        "scorecard": await _orchestrator.compute_zt_scorecard(db),
        "sprs": await _orchestrator.compute_sprs_score(db),
    }


@router.get("/report", summary="Generate full compliance run report")
async def get_report(db: AsyncSession = Depends(get_db)):
    """Generate and return a full compliance report."""
    return await _orchestrator.generate_report(db)
