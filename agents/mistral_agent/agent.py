"""
Mistral AI Agent for CMMC Compliance Analysis
AGI Corporation 2026

This agent uses Mistral AI models (mistral-large, mistral-medium, codestral)
to analyze compliance gaps, generate remediation guidance, assess control
implementation evidence, and produce POAM recommendations.

Mistral is the preferred AI backbone because:
- Mistral Large 2 is competitive with GPT-4 for structured reasoning
- Codestral for DevSecOps pipeline/code analysis
- Mistral 7B (local via Ollama) for air-gapped / classified environments
- Function calling support for MCP tool integration
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from mistralai import Mistral
from pydantic import BaseModel


# ─── Mistral Configuration ─────────────────────────────────────────────────────
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_CODE_MODEL = os.getenv("MISTRAL_CODE_MODEL", "codestral-latest")
MISTRAL_LOCAL_MODEL = os.getenv("MISTRAL_LOCAL_MODEL", "mistral")
USE_LOCAL = os.getenv("USE_LOCAL_MODEL", "false").lower() == "true"


class MistralComplianceAgent:
    """
    Mistral-powered compliance agent.
    
    Responsibilities:
    - Gap analysis: identify unimplemented controls vs ZT pillars
    - Evidence evaluation: score evidence quality (0-1 confidence)
    - Remediation guidance: step-by-step fix recommendations
    - POAM generation: structured plan of action & milestones
    - Code review: DevSecOps pipeline security analysis (Codestral)
    - Natural language Q&A: answer CMMC/ZT questions for assessors
    """

    def __init__(self):
        if USE_LOCAL:
            # Use Ollama local endpoint for air-gapped environments
            from openai import OpenAI
            self.client = OpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama",
            )
            self.model = MISTRAL_LOCAL_MODEL
            self.use_mistral_client = False
        else:
            self.client = Mistral(api_key=MISTRAL_API_KEY)
            self.model = MISTRAL_MODEL
            self.code_model = MISTRAL_CODE_MODEL
            self.use_mistral_client = True

    def _chat(self, system: str, user: str, model: Optional[str] = None) -> str:
        """Send a chat completion request to Mistral."""
        m = model or self.model
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if self.use_mistral_client:
            response = self.client.chat.complete(
                model=m,
                messages=messages,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        else:
            response = self.client.chat.completions.create(
                model=m, messages=messages
            )
            return response.choices[0].message.content

    def analyze_gap(
        self,
        control_id: str,
        control_title: str,
        control_description: str,
        zt_pillar: str,
        current_status: str,
        existing_evidence: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze a single CMMC control for compliance gaps.
        Returns structured gap analysis with confidence score.
        """
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

        result = self._chat(system, user)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw_response": result, "error": "parse_failed"}

    def evaluate_evidence(
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

        result = self._chat(system, user)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"confidence_score": 0.5, "coverage_rating": "partial"}

    def analyze_code_security(
        self,
        code_snippet: str,
        language: str = "python",
        relevant_controls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        DevSecOps: Analyze code for security issues mapped to CMMC controls.
        Uses Codestral model for code-specific analysis.
        """
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
        result = self._chat(system, user, model=model)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"overall_risk": "unknown", "raw": result}

    def generate_sprs_narrative(
        self, score: int, domain_breakdown: Dict[str, Any]
    ) -> str:
        """Generate a human-readable SPRS score narrative for assessors."""
        system = """You are a DoD cybersecurity assessor. Generate a concise narrative
        (3-4 paragraphs) explaining the SPRS score, domain gaps, and priority actions.
        The narrative will be included in a System Security Plan."""
        user = f"""SPRS Score: {score} (range: -203 to 110)
        Domain Breakdown: {json.dumps(domain_breakdown, indent=2)}
        Generate the SSP narrative section."""
        if self.use_mistral_client:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content

    def answer_compliance_question(self, question: str, context: str = "") -> str:
        """Answer a natural language CMMC/ZT compliance question."""
        system = """You are a CMMC 2.0 and DoD Zero Trust compliance expert.
        Answer the question clearly, citing specific CMMC practices and ZT capabilities.
        Be concise and practical."""
        user = f"{context}\n\nQuestion: {question}" if context else question
        if self.use_mistral_client:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content


# ─── FastAPI router for Mistral agent endpoints ────────────────────────────────
from fastapi import APIRouter, HTTPException

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
async def gap_analysis(req: GapAnalysisRequest):
    """Use Mistral to analyze a compliance gap and return remediation steps."""
    try:
        result = agent.analyze_gap(
            req.control_id, req.control_title, req.control_description,
            req.zt_pillar, req.current_status, req.existing_evidence
        )
        return {"control_id": req.control_id, "analysis": result, "model": MISTRAL_MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-review", summary="DevSecOps code security analysis with Codestral")
async def code_review(req: CodeReviewRequest):
    """Use Codestral to analyze code for CMMC-mapped security issues."""
    try:
        result = agent.analyze_code_security(
            req.code_snippet, req.language, req.relevant_controls
        )
        return {"analysis": result, "model": MISTRAL_CODE_MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", summary="Ask a CMMC/ZT compliance question")
async def ask_question(req: QuestionRequest):
    """Natural language CMMC compliance Q&A powered by Mistral."""
    try:
        answer = agent.answer_compliance_question(req.question, req.context)
        return {"question": req.question, "answer": answer, "model": MISTRAL_MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
