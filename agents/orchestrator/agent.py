"""
CMMC Compliance Orchestrator Agent
AGI Corporation 2026

The Orchestrator is the top-level coordinator in the agent network.
It maintains the compliance knowledge graph, routes tasks to specialist
agents, aggregates evidence, and generates unified compliance scorecards.

Aligns with DoD ZT Orchestration/Automation pillar and Fulcrum LOE 3/4.
"""
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field


class AgentType(str, Enum):
    ICAM = "icam"                     # Identity/Credential/Access Mgmt
    DATA = "data_protection"           # Data-centric security
    INFRA = "infrastructure"           # Network/micro-segmentation
    DEVSECOPS = "devsecops"            # DevSecOps/supply chain
    GOVERNANCE = "governance"          # Policy/risk/POA&M
    OPS = "operations"                 # IR/SIEM/SOAR
    MISTRAL = "mistral"                # AI analysis engine


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
    scope: str = ""                    # system name or service
    required_controls: List[str] = field(default_factory=list)
    assigned_agents: List[AgentType] = field(default_factory=list)
    status: str = "pending"           # pending/running/completed/failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    findings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlStatus:
    """Canonical control status record - shared schema for all agents."""
    control_id: str
    zt_pillar: str
    status: str                        # implemented/partial/planned/not_implemented
    confidence: float                  # 0.0-1.0 ZT confidence score
    evidence_ids: List[str] = field(default_factory=list)
    owner_agent: AgentType = AgentType.GOVERNANCE
    last_updated: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""


class ComplianceOrchestrator:
    """
    Central orchestrator that:
    1. Decomposes compliance tasks into agent-specific sub-tasks
    2. Aggregates agent outputs into unified ControlStatus records
    3. Computes ZT pillar maturity scores and SPRS score
    4. Generates dashboard-ready scorecards
    5. Routes incidents to IR agent and code pushes to DevSecOps agent
    """

    # ZT Pillar -> CMMC domains mapping (DoD ZT Strategy alignment)
    ZT_DOMAIN_MAP = {
        "User": ["AC", "IA", "PS"],
        "Device": ["CM", "MA", "PE"],
        "Network": ["SC", "AC"],
        "Application": ["CM", "CA", "SI"],
        "Data": ["MP", "SC", "AU"],
        "Visibility & Analytics": ["AU", "IR", "RA"],
        "Automation & Orchestration": ["IR", "SI", "CA"],
    }

    # SPRS weights per CMMC domain (from NIST 800-171 DoD Assessment Methodology)
    DOMAIN_WEIGHTS = {
        "AC": 22, "AU": 9, "CM": 9, "IA": 11, "IR": 3,
        "MA": 6, "MP": 9, "PS": 2, "PE": 6, "RA": 5,
        "CA": 4, "SA": 1, "SC": 16, "SI": 7,
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
            task.assigned_agents = [AgentType.DEVSECOPS, AgentType.ICAM, AgentType.MISTRAL]
            task.required_controls = task.required_controls or ["SI.2.214", "CM.2.061", "AC.1.001"]
        elif trigger == TaskTrigger.INCIDENT:
            task.assigned_agents = [AgentType.OPS, AgentType.MISTRAL]
            task.required_controls = task.required_controls or ["IR.2.092", "AU.2.041"]
        elif trigger == TaskTrigger.ASSESSMENT:
            task.assigned_agents = list(AgentType)
        else:
            task.assigned_agents = [AgentType.GOVERNANCE, AgentType.MISTRAL]

        self.task_queue.append(task)
        return task

    def update_control(
        self,
        control_id: str,
        zt_pillar: str,
        status: str,
        confidence: float,
        evidence_ids: List[str],
        owner_agent: AgentType,
        notes: str = "",
    ) -> ControlStatus:
        """Update a control's status from any agent output."""
        cs = ControlStatus(
            control_id=control_id,
            zt_pillar=zt_pillar,
            status=status,
            confidence=confidence,
            evidence_ids=evidence_ids,
            owner_agent=owner_agent,
            notes=notes,
        )
        self.control_registry[control_id] = cs
        return cs

    def compute_sprs_score(self) -> Dict[str, Any]:
        """Compute SPRS score from control registry (max 110, floor -203)."""
        domain_scores = {d: 0 for d in self.DOMAIN_WEIGHTS}
        domain_totals = {d: 0 for d in self.DOMAIN_WEIGHTS}

        for ctrl_id, cs in self.control_registry.items():
            domain = ctrl_id.split(".")[0] if "." in ctrl_id else None
            if domain and domain in domain_scores:
                domain_totals[domain] += 1
                if cs.status == "implemented":
                    domain_scores[domain] += 1
                elif cs.status == "partial":
                    domain_scores[domain] += 0.5

        sprs = 110
        for domain, weight in self.DOMAIN_WEIGHTS.items():
            total = domain_totals.get(domain, 1)
            implemented = domain_scores.get(domain, 0)
            if total > 0:
                pct = implemented / total
                # Each unimplemented control reduces SPRS by its weight / total in domain
                shortfall = (1 - pct) * weight
                sprs -= shortfall

        return {
            "sprs_score": round(max(-203, sprs), 1),
            "domain_breakdown": {
                d: {
                    "implemented": domain_scores[d],
                    "total": domain_totals.get(d, 0),
                    "weight": self.DOMAIN_WEIGHTS[d],
                }
                for d in self.DOMAIN_WEIGHTS
            },
        }

    def compute_zt_scorecard(self) -> List[Dict[str, Any]]:
        """Generate per-ZT-pillar maturity scorecard."""
        scorecard = []
        for pillar, domains in self.ZT_DOMAIN_MAP.items():
            pillar_controls = [
                cs for ctrl_id, cs in self.control_registry.items()
                if cs.zt_pillar == pillar or ctrl_id.split(".")[0] in domains
            ]
            if not pillar_controls:
                continue
            total = len(pillar_controls)
            implemented = sum(1 for c in pillar_controls if c.status == "implemented")
            partial = sum(1 for c in pillar_controls if c.status == "partial")
            avg_confidence = (
                sum(c.confidence for c in pillar_controls) / total if total > 0 else 0
            )
            scorecard.append({
                "pillar": pillar,
                "total_controls": total,
                "implemented": implemented,
                "partial": partial,
                "not_implemented": total - implemented - partial,
                "maturity_pct": round((implemented + 0.5 * partial) / total * 100, 1),
                "confidence_avg": round(avg_confidence, 2),
            })
        return scorecard

    def generate_report(self) -> Dict[str, Any]:
        """Generate a complete compliance run report."""
        sprs_data = self.compute_sprs_score()
        zt_scorecard = self.compute_zt_scorecard()
        total = len(self.control_registry)
        implemented = sum(
            1 for cs in self.control_registry.values() if cs.status == "implemented"
        )
        return {
            "report_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "sprs_score": sprs_data["sprs_score"],
            "sprs_domain_breakdown": sprs_data["domain_breakdown"],
            "zt_scorecard": zt_scorecard,
            "overall_compliance_pct": round(implemented / total * 100, 1) if total else 0,
            "total_controls": total,
            "controls_implemented": implemented,
            "evidence_artifacts": len(self.evidence_store),
            "tasks_completed": len(self.completed_tasks),
            "agent_runs": self.agent_runs,
        }


# FastAPI endpoint integration
from fastapi import APIRouter

router = APIRouter()
_orchestrator = ComplianceOrchestrator()


@router.post("/task", summary="Create and route a compliance task")
async def create_task(trigger: str, scope: str, controls: str = ""):
    """Create a new orchestrated compliance task."""
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


@router.get("/scorecard", summary="Get ZT pillar compliance scorecard")
async def get_scorecard():
    """Return current ZT pillar maturity scorecard."""
    return {
        "scorecard": _orchestrator.compute_zt_scorecard(),
        "sprs": _orchestrator.compute_sprs_score(),
    }


@router.get("/report", summary="Generate full compliance run report")
async def get_report():
    """Generate and return a full compliance report."""
    return _orchestrator.generate_report()
