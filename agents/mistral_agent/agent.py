"""
Mistral AI Agent for CMMC Compliance Analysis
AGI Corporation 2026

This agent uses Mistral AI models (mistral-large, mistral-medium, codestral)
to analyze compliance gaps, generate remediation guidance, assess control
implementation evidence, and produce POAM recommendations.
"""
import os
import json
import uuid
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any
try:
    from mistralai import Mistral as _MistralClient
    _MISTRAL_SDK_V1 = True
except ImportError:
    try:
        from mistralai.client import MistralClient as _MistralClient  # type: ignore[assignment]
        _MISTRAL_SDK_V1 = False
    except ImportError:
        _MistralClient = None  # type: ignore[assignment,misc]
        _MISTRAL_SDK_V1 = False
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import AgentRunRecord, get_db

# ─── Mistral Configuration ─────────────────────────────────────────────────────
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_CODE_MODEL = os.getenv("MISTRAL_CODE_MODEL", "codestral-latest")
MISTRAL_LOCAL_MODEL = os.getenv("MISTRAL_LOCAL_MODEL", "mistral")
USE_LOCAL = os.getenv("USE_LOCAL_MODEL", "false").lower() == "true"


class MistralComplianceAgent:
    """
    Mistral-powered compliance agent.
    """

    def __init__(self):
        if USE_LOCAL:
            # Use Ollama local endpoint for air-gapped environments
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama",
            )
            self.model = MISTRAL_LOCAL_MODEL
            self.use_mistral_client = False
        else:
            if not MISTRAL_API_KEY:
                self.client = None
                print("Warning: MISTRAL_API_KEY not set. Mistral agent will operate in mock mode.")
            else:
                self.client = _MistralClient(api_key=MISTRAL_API_KEY) if _MistralClient else None
            self.model = MISTRAL_MODEL
            self.code_model = MISTRAL_CODE_MODEL
            self.use_mistral_client = True

    async def _chat(self, system: str, user: str, model: Optional[str] = None) -> str:
        """Send a chat completion request to Mistral."""
        if not self.client:
            # Return mock JSON response if no client
            return json.dumps({
                "gap_summary": "Mock analysis: Mistral API key missing.",
                "severity": "medium",
                "zt_impact": "Simulated impact on ZT pillar.",
                "confidence_score": 0.5,
                "remediation_steps": ["Configure MISTRAL_API_KEY"],
                "estimated_effort_days": 1,
                "poam_entry": {"milestone": "Setup API", "completion_date": "TBD", "responsible_party": "Admin", "resources": "API Key"},
                "overall_risk": "medium",
                "security_issues": []
            })

        m = model or self.model
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if self.use_mistral_client:
            response = await self.client.chat.complete_async(
                model=m,
                messages=messages,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        else:
            response = await self.client.chat.completions.create(
                model=m, messages=messages, response_format={"type": "json_object"}
            )
            return response.choices[0].message.content

    async def record_run(self, db: AsyncSession, trigger: str, scope: str, controls: List[str], findings: Dict[str, Any], status: str = "completed"):
        record = AgentRunRecord(
            id=str(uuid.uuid4()),
            agent_type="mistral",
            trigger=trigger,
            scope=scope,
            controls_evaluated=controls,
            findings=findings,
            status=status,
            mistral_model=self.model,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC)
        )
        db.add(record)
        await db.commit()
        return record.id

    async def analyze_gap(
        self,
        control_id: str,
        control_title: str,
        control_description: str,
        zt_pillar: str,
        current_status: str,
        existing_evidence: List[str],
    ) -> Dict[str, Any]:
        system = """You are a CMMC Level 2 compliance expert and DoD Zero Trust advisor.
        Analyze the provided control and return a JSON object with these fields:
        - gap_summary: string describing the compliance gap
        - severity: "critical" | "high" | "medium" | "low"
        - zt_impact: how this gap affects the ZT pillar
        - confidence_score: float 0.0-1.0 (how well existing evidence covers the control)
        - remediation_steps: list of strings with ordered action steps
        - estimated_effort_days: integer
        - poam_entry: object with {milestone, completion_date, responsible_party, resources}
        """
        user = f"""Control: {control_id} - {control_title}
        Description: {control_description}
        ZT Pillar: {zt_pillar}
        Current Status: {current_status}
        Existing Evidence: {json.dumps(existing_evidence)}
        
        Analyze this control for compliance gaps and provide remediation guidance."""

        result = await self._chat(system, user)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw_response": result, "error": "parse_failed"}

    async def evaluate_evidence(
        self,
        control_id: str,
        evidence_descriptions: List[str],
    ) -> Dict[str, Any]:
        """
        Score evidence quality for a given control.
        Returns confidence score and coverage gaps.
        """
        system = """You are a CMMC assessor evaluating evidence artifacts.
        Return a JSON object with:
        - confidence_score: float 0.0-1.0
        - coverage_rating: "full" | "substantial" | "partial" | "insufficient"
        - missing_evidence_types: list of strings
        - quality_notes: string
        """
        user = f"""Control ID: {control_id}
        Evidence provided: {json.dumps(evidence_descriptions)}
        Rate the completeness and quality of this evidence."""

        result = await self._chat(system, user)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"confidence_score": 0.5, "coverage_rating": "partial"}

    async def analyze_code_security(
        self,
        code_snippet: str,
        language: str = "python",
        relevant_controls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        system = """You are a DevSecOps security expert analyzing code for CMMC compliance.
        Return a JSON object with:
        - security_issues: list of {severity, line, description, cmmc_control, fix}
        - overall_risk: "critical" | "high" | "medium" | "low" | "pass"
        - affected_controls: list of CMMC control IDs
        - recommended_fixes: list of strings
        - sbom_concerns: list of dependency/supply-chain concerns
        """
        user = f"""Language: {language}
        Relevant Controls: {json.dumps(relevant_controls or [])}
        
        Code to analyze:
        ```{language}
        {code_snippet}
        ```
        """
        model = self.code_model if self.use_mistral_client else self.model
        result = await self._chat(system, user, model=model)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"overall_risk": "unknown", "raw": result}

    async def generate_sprs_narrative(
        self, score: int, domain_breakdown: Dict[str, Any]
    ) -> str:
        """Generate a human-readable SPRS score narrative for assessors."""
        if not self.client:
            return "Mock narrative: Mistral API key missing. SPRS score reflects current assessment state."

        system = """You are a DoD cybersecurity assessor. Generate a concise narrative
        (3-4 paragraphs) explaining the SPRS score, domain gaps, and priority actions.
        The narrative will be included in a System Security Plan."""
        user = f"""SPRS Score: {score} (range: -203 to 110)
        Domain Breakdown: {json.dumps(domain_breakdown, indent=2)}
        Generate the SSP narrative section."""

        if self.use_mistral_client:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content

    async def answer_compliance_question(self, question: str, context: str = "") -> str:
        if not self.client:
            return "Mock answer: Mistral API key missing. Please configure it to get real compliance advice."

        system = """You are a CMMC 2.0 and DoD Zero Trust compliance expert.
        Answer the question clearly, citing specific CMMC practices and ZT capabilities.
        Be concise and practical."""
        user = f"{context}\n\nQuestion: {question}" if context else question
        if self.use_mistral_client:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content


# ─── FastAPI router for Mistral agent endpoints ────────────────────────────────
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter()
agent = MistralComplianceAgent()


class GapAnalysisRequest(BaseModel):
    control_id: str
    control_title: str
    control_description: str
    zt_pillar: str
    current_status: str = "not_implemented"
    existing_evidence: List[str] = []


class CodeReviewRequest(BaseModel):
    code_snippet: str
    language: str = "python"
    relevant_controls: Optional[List[str]] = None


class QuestionRequest(BaseModel):
    question: str
    context: str = ""


@router.post("/gap-analysis", summary="Analyze CMMC control gap with Mistral AI")
async def gap_analysis(req: GapAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """Use Mistral to analyze a compliance gap and return remediation steps."""
    try:
        result = await agent.analyze_gap(
            req.control_id, req.control_title, req.control_description,
            req.zt_pillar, req.current_status, req.existing_evidence
        )
        await agent.record_run(db, "manual", f"Gap Analysis: {req.control_id}", [req.control_id], result)
        return {"control_id": req.control_id, "analysis": result, "model": MISTRAL_MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-review", summary="DevSecOps code security analysis with Codestral")
async def code_review(req: CodeReviewRequest, db: AsyncSession = Depends(get_db)):
    """Use Codestral to analyze code for CMMC-mapped security issues."""
    try:
        result = await agent.analyze_code_security(
            req.code_snippet, req.language, req.relevant_controls
        )
        await agent.record_run(db, "manual", "Code Review", req.relevant_controls or [], result)
        return {"analysis": result, "model": MISTRAL_CODE_MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", summary="Ask a CMMC/ZT compliance question")
async def ask_question(req: QuestionRequest):
    """Natural language CMMC compliance Q&A powered by Mistral."""
    try:
        answer = await agent.answer_compliance_question(req.question, req.context)
        return {"question": req.question, "answer": answer, "model": MISTRAL_MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
