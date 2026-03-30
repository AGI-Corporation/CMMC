"""
OML 1.0 Model Fingerprinting Router
AGI Corporation CMMC Platform 2026

REST endpoints for registering, verifying, and auditing AI model fingerprints
based on the Sentient Foundation OML 1.0 specification.

CMMC Control Mappings:
  - SA.L2-3.14.7  Supply-chain risk management (AI model provenance)
  - SI.L1-3.14.1  System/software integrity (fingerprint integrity checks)
  - IA.L2-3.5.10  Replay-resistant authentication for AI components
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import oml_fingerprint_service as fps

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

CMMC_CONTROLS = ["SA.L2-3.14.7", "SI.L1-3.14.1", "IA.L2-3.5.10"]


class RegisterRequest(BaseModel):
    model_id: str = Field(..., description="AI model identifier, e.g. 'gpt-4o'")
    provider: str = Field(..., description="AI provider, e.g. 'openai'")
    probe_responses: list[str] = Field(
        ...,
        description="Ordered list of model responses to each OML probe prompt",
    )


class VerifyRequest(BaseModel):
    model_id: str = Field(..., description="AI model identifier to verify")
    probe_responses: list[str] = Field(
        ...,
        description="Fresh ordered list of model responses to the OML probe prompts",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/probes",
    summary="Get OML probe prompts",
    description=(
        "Return the standardised OML 1.0 probe prompts that must be submitted to "
        "the AI model before calling /register or /verify. "
        "Maps to CMMC SA.L2-3.14.7."
    ),
)
async def get_probes() -> dict:
    probes = fps.get_probe_prompts()
    return {
        "probes": probes,
        "count": len(probes),
        "cmmc_controls": CMMC_CONTROLS,
        "instructions": (
            "Send each probe to your AI model in order and collect the responses. "
            "Then call POST /register with the responses to fingerprint the model, "
            "or POST /verify to check an already-registered model."
        ),
    }


@router.post(
    "/register",
    summary="Register model fingerprints",
    description=(
        "Generate and store OML 1.0 cryptographic fingerprints for an AI model. "
        "Each (probe_query, response) pair is stored as a HMAC-signed fingerprint. "
        "Maps to CMMC SA.L2-3.14.7 and SI.L1-3.14.1."
    ),
    status_code=201,
)
async def register_model(req: RegisterRequest) -> dict:
    probe_count = len(fps.get_probe_prompts())
    if len(req.probe_responses) < probe_count:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Expected {probe_count} probe responses "
                f"(one per OML probe prompt), got {len(req.probe_responses)}."
            ),
        )

    record = fps.generate_fingerprints(
        req.model_id, req.provider, req.probe_responses
    )
    return {
        "model_id": record.model_id,
        "provider": record.provider,
        "model_hash": record.model_hash,
        "fingerprint_count": len(record.fingerprints),
        "registered_at": record.registered_at,
        "chain_hash": record.chain_hash,
        "verification_status": record.verification_status,
        "cmmc_controls": CMMC_CONTROLS,
    }


@router.post(
    "/verify",
    summary="Verify model fingerprints",
    description=(
        "Challenge a registered AI model with the OML probe prompts and verify "
        "that the responses match the stored fingerprints. A pass rate ≥ the "
        "configured OML_MIN_PASS_RATE (default 0.75) is required for verification "
        "to succeed. Failures indicate possible model substitution or tampering. "
        "Maps to CMMC SA.L2-3.14.7, SI.L1-3.14.1, and IA.L2-3.5.10."
    ),
)
async def verify_model(req: VerifyRequest) -> dict:
    result = fps.verify_model(req.model_id, req.probe_responses)
    return {
        "model_id": result.model_id,
        "verified": result.verified,
        "pass_rate": result.pass_rate,
        "passed": result.passed,
        "failed": result.failed,
        "total_challenges": result.total_challenges,
        "timestamp": result.timestamp,
        "audit_chain_id": result.audit_chain_id,
        "cmmc_controls": CMMC_CONTROLS,
    }


@router.get(
    "/registry",
    summary="List registered model fingerprints",
    description=(
        "Return a summary of all AI models registered with OML fingerprints. "
        "Raw fingerprint hashes are not exposed. "
        "Maps to CMMC SA.L2-3.14.7."
    ),
)
async def get_registry() -> dict:
    registry = fps.get_registry()
    return {
        "registered_models": registry,
        "count": len(registry),
        "cmmc_controls": CMMC_CONTROLS,
    }


@router.get(
    "/audit",
    summary="Fingerprint audit log",
    description=(
        "Return the Merkle-chained audit log of all fingerprint registration and "
        "verification events. Each entry links to the previous entry via "
        "prev_hash → chain_hash, providing tamper-evident provenance. "
        "Maps to CMMC SI.L1-3.14.1."
    ),
)
async def get_audit_log() -> dict:
    log = fps.get_audit_log()
    return {
        "audit_log": log,
        "count": len(log),
        "cmmc_controls": CMMC_CONTROLS,
    }
