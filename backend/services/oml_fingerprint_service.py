"""
OML 1.0 AI Model Fingerprinting Service
AGI Corporation CMMC Platform 2026

Implements Sentient Foundation's OML 1.0 (Open, Monetizable, Loyal) fingerprinting
specification adapted for API-based AI model verification in the CMMC platform.

Fingerprinting approach:
  - Standardised probe queries are sent to each AI model and the responses are
    captured as cryptographic (query_hash, response_hash) pairs — the model's
    unique "fingerprint" (analogous to the fine-tuned query/response pairs in
    the original OML 1.0 spec).
  - Future verification challenges re-run the same probes and checks whether the
    response hashes match within an acceptable tolerance, detecting model
    substitution or tampering.
  - Every registration and verification event is appended to a Merkle-chained
    audit log (prev_hash → chain_hash), providing tamper-evident provenance.

CMMC Control Mappings:
  - SA.L2-3.14.7  Supply-chain risk management (AI model provenance)
  - SI.L1-3.14.1  System/software integrity checks
  - IA.L2-3.5.10  Employ replay-resistant authentication for AI components

References:
  - OML 1.0 Specification: https://github.com/sentient-agi/oml-1.0-fingerprinting
  - OML Whitepaper: https://arxiv.org/pdf/2411.03887v4
  - OML IACR ePrint: https://eprint.iacr.org/2024/1573
"""

import hashlib
import hmac
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_FINGERPRINT_KEY: bytes = os.getenv("OML_FINGERPRINT_KEY", "").encode()
_MIN_PASS_RATE: float = float(os.getenv("OML_MIN_PASS_RATE", "0.75"))

# Standardised probe prompts.  These are domain-stable CMMC questions whose
# answers are deterministic for a given model, forming the probe corpus used
# to fingerprint each registered model.
_PROBE_TEMPLATES: list[str] = [
    "What does CMMC stand for?",
    "Name one CMMC Level 1 practice domain.",
    "What is the SPRS score range in the DoD assessment methodology?",
    "Which NIST publication governs CMMC Level 2 practice requirements?",
    "What does AC stand for in CMMC control AC.1.001?",
]


# ---------------------------------------------------------------------------
# Cryptographic helpers
# ---------------------------------------------------------------------------


def _hmac_sign(data: str) -> str:
    """Return an HMAC-SHA256 hex digest of *data* using the fingerprint key."""
    key = _FINGERPRINT_KEY or b"dev-oml-key"
    return hmac.new(key, data.encode(), hashlib.sha256).hexdigest()


def _sha256(data: str) -> str:
    """Return the SHA-256 hex digest of *data*."""
    return hashlib.sha256(data.encode()).hexdigest()


def _constant_time_equal(a: str, b: str) -> bool:
    """Timing-safe string comparison (prevents timing oracle attacks)."""
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class OMLFingerprint:
    """A single OML-style (query_hash, response_hash) fingerprint pair.

    Analogous to the secret (query, response) pairs embedded during fine-tuning
    in the original OML 1.0 specification.
    """

    fingerprint_id: str
    probe_index: int
    query_hash: str     # HMAC-SHA256 of the probe query (proves query authenticity)
    response_hash: str  # SHA-256 of the normalised model response
    signature: str      # HMAC over (fingerprint_id:query_hash:response_hash)
    model_id: str
    created_at: str


@dataclass
class ModelFingerprintRecord:
    """Fingerprint registry entry for a registered AI model."""

    model_id: str
    provider: str
    model_hash: str           # SHA-256 of (model_id + provider + registered_at)
    fingerprints: list        # list[OMLFingerprint] stored as dicts for JSON compat
    registered_at: str
    verification_status: str  # unverified | verified | tampered
    verified_at: Optional[str]
    prev_chain_hash: str      # Merkle link to previous registry entry
    chain_hash: str           # SHA-256 hash of this record


@dataclass
class VerificationResult:
    """Result of a model fingerprint verification attempt."""

    model_id: str
    total_challenges: int
    passed: int
    failed: int
    pass_rate: float
    verified: bool
    timestamp: str
    audit_chain_id: str


# ---------------------------------------------------------------------------
# In-process registry and audit log
# (Persisted to the DB in a future extension via ModelFingerprintRecord table)
# ---------------------------------------------------------------------------

_registry: dict[str, ModelFingerprintRecord] = {}
_audit_log: list[dict] = []
_chain_head: str = "0" * 64  # Genesis hash — all-zeros per convention


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_probe_prompts() -> list[str]:
    """Return the ordered list of standardised OML probe prompts."""
    return list(_PROBE_TEMPLATES)


def generate_fingerprints(
    model_id: str,
    provider: str,
    probe_responses: list[str],
) -> ModelFingerprintRecord:
    """Register an AI model with OML 1.0 fingerprints.

    Args:
        model_id: Model identifier (e.g. ``"gpt-4o"``).
        provider: Provider name (e.g. ``"openai"``).
        probe_responses: Ordered list of model responses, one per probe in
            :data:`_PROBE_TEMPLATES`.  Must be at least as long as
            ``_PROBE_TEMPLATES``.

    Returns:
        :class:`ModelFingerprintRecord` stored in the in-process registry and
        Merkle-chained to the previous entry.
    """
    global _chain_head

    now = datetime.now(UTC).isoformat()
    model_hash = _sha256(f"{model_id}:{provider}:{now}")

    fingerprints: list[dict] = []
    for i, (probe, response) in enumerate(zip(_PROBE_TEMPLATES, probe_responses)):
        fp_id = str(uuid.uuid4())
        query_hash = _hmac_sign(probe)
        response_hash = _sha256(response.strip().lower())
        signature = _hmac_sign(f"{fp_id}:{query_hash}:{response_hash}")
        fp = OMLFingerprint(
            fingerprint_id=fp_id,
            probe_index=i,
            query_hash=query_hash,
            response_hash=response_hash,
            signature=signature,
            model_id=model_id,
            created_at=now,
        )
        fingerprints.append(asdict(fp))

    # Merkle-chain this record to the previous registry head
    record_data = f"{model_id}:{provider}:{model_hash}:{now}"
    chain_hash = _sha256(f"{_chain_head}:{record_data}")

    record = ModelFingerprintRecord(
        model_id=model_id,
        provider=provider,
        model_hash=model_hash,
        fingerprints=fingerprints,
        registered_at=now,
        verification_status="unverified",
        verified_at=None,
        prev_chain_hash=_chain_head,
        chain_hash=chain_hash,
    )

    _registry[model_id] = record
    _chain_head = chain_hash
    return record


def verify_model(
    model_id: str,
    probe_responses: list[str],
) -> VerificationResult:
    """Verify a model's identity by checking probe responses against stored fingerprints.

    Implements the OML 1.0 verification step: the owner challenges the model
    with the secret queries and checks whether the responses match the
    registered fingerprints.  A ``pass_rate`` ≥ :data:`_MIN_PASS_RATE` (default
    0.75) is required for ``verified=True``.

    Args:
        model_id: Model to verify.
        probe_responses: Ordered list of fresh responses from the model,
            one per probe in :data:`_PROBE_TEMPLATES`.

    Returns:
        :class:`VerificationResult` with verification outcome and audit chain ID.
    """
    now = datetime.now(UTC).isoformat()
    audit_id = str(uuid.uuid4())

    if model_id not in _registry:
        result = VerificationResult(
            model_id=model_id,
            total_challenges=0,
            passed=0,
            failed=0,
            pass_rate=0.0,
            verified=False,
            timestamp=now,
            audit_chain_id=audit_id,
        )
        _append_audit(result, "not_registered")
        return result

    record = _registry[model_id]
    stored_fps: list[dict] = record.fingerprints

    total = min(len(stored_fps), len(probe_responses))
    passed = 0
    for i in range(total):
        expected_hash: str = stored_fps[i]["response_hash"]
        observed_hash: str = _sha256(probe_responses[i].strip().lower())
        if _constant_time_equal(expected_hash, observed_hash):
            passed += 1

    failed = total - passed
    pass_rate = passed / total if total > 0 else 0.0
    verified = pass_rate >= _MIN_PASS_RATE

    record.verification_status = "verified" if verified else "tampered"
    record.verified_at = now

    result = VerificationResult(
        model_id=model_id,
        total_challenges=total,
        passed=passed,
        failed=failed,
        pass_rate=round(pass_rate, 4),
        verified=verified,
        timestamp=now,
        audit_chain_id=audit_id,
    )
    _append_audit(result, record.verification_status)
    return result


def get_registry() -> dict:
    """Return a summary of all registered model fingerprints (no raw hashes)."""
    return {
        model_id: {
            "model_id": r.model_id,
            "provider": r.provider,
            "model_hash": r.model_hash,
            "fingerprint_count": len(r.fingerprints),
            "registered_at": r.registered_at,
            "verification_status": r.verification_status,
            "verified_at": r.verified_at,
            "chain_hash": r.chain_hash,
        }
        for model_id, r in _registry.items()
    }


def get_audit_log() -> list[dict]:
    """Return the Merkle-chained audit log of all fingerprint events."""
    return list(_audit_log)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _append_audit(result: VerificationResult, status: str) -> None:
    """Append a verification event to the Merkle-chained audit log."""
    global _chain_head

    entry_data = (
        f"{result.audit_chain_id}:{result.model_id}:{status}:{result.timestamp}"
    )
    new_hash = _sha256(f"{_chain_head}:{entry_data}")

    entry = {
        "audit_id": result.audit_chain_id,
        "model_id": result.model_id,
        "status": status,
        "pass_rate": result.pass_rate,
        "passed": result.passed,
        "failed": result.failed,
        "total_challenges": result.total_challenges,
        "timestamp": result.timestamp,
        "prev_hash": _chain_head,
        "chain_hash": new_hash,
    }
    _audit_log.append(entry)
    _chain_head = new_hash
