"""
CMMC Compliance Orchestrator Agent
AGI Corporation 2026

The Orchestrator is the top-level coordinator in the agent network.
It maintains the compliance knowledge graph, routes tasks to specialist
agents, aggregates evidence, and generates unified compliance scorecards.

Aligns with DoD ZT Orchestration/Automation pillar and Fulcrum LOE 3/4.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (AgentRunRecord, AssessmentRecord,
                                 ControlRecord, get_db, get_latest_assessments)


class AgentType(str, Enum):
    ICAM = "icam"  # Identity/Credential/Access Mgmt
    DATA = "data_protection"  # Data-centric security
    INFRA = "infrastructure"  # Network/micro-segmentation
    DEVSECOPS = "devsecops"  # DevSecOps/supply chain
    GOVERNANCE = "governance"  # Policy/risk/POA&M
    OPS = "operations"  # IR/SIEM/SOAR
    MISTRAL = "mistral"  # AI analysis engine


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
            task.assigned_agents = [AgentType.OPS, AgentType.MISTRAL]
            task.required_controls = task.required_controls or ["IR.2.092", "AU.2.041"]
        elif trigger == TaskTrigger.ASSESSMENT:
            task.assigned_agents = list(AgentType)
        else:
            task.assigned_agents = [AgentType.GOVERNANCE, AgentType.MISTRAL]

        self.task_queue.append(task)
        return task

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
                    elif status == "partially_implemented" or status == "partial":
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


# FastAPI endpoint integration
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
