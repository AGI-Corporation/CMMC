"""
Tests for OML 1.0 AI Model Fingerprinting service and API endpoints.
AGI Corporation CMMC Platform 2026

Validates fingerprint generation, verification, audit-log chaining,
and the REST API surface exposed via /api/fingerprint/*.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.services import oml_fingerprint_service as fps

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROBE_COUNT = len(fps.get_probe_prompts())

# Simulated "correct" responses — identical content will always pass
CORRECT_RESPONSES = [
    "Cybersecurity Maturity Model Certification",
    "Access Control",
    "-203 to 110",
    "NIST SP 800-171",
    "Access Control",
][:PROBE_COUNT]

# Simulated "wrong" responses — different content, causes fingerprint mismatch
WRONG_RESPONSES = ["wrong answer"] * PROBE_COUNT


@pytest.fixture(autouse=True)
def reset_registry():
    """Ensure the in-process registry and audit log are clean before each test."""
    fps._registry.clear()
    fps._audit_log.clear()
    fps._chain_head = "0" * 64
    yield


# ---------------------------------------------------------------------------
# Service-layer unit tests
# ---------------------------------------------------------------------------


def test_get_probe_prompts_returns_list():
    probes = fps.get_probe_prompts()
    assert isinstance(probes, list)
    assert len(probes) > 0


def test_generate_fingerprints_creates_registry_entry():
    record = fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    assert record.model_id == "gpt-4o"
    assert record.provider == "openai"
    assert len(record.fingerprints) == PROBE_COUNT
    assert record.verification_status == "unverified"
    assert record.chain_hash != "0" * 64


def test_generate_fingerprints_stored_in_registry():
    fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    registry = fps.get_registry()
    assert "gpt-4o" in registry
    assert registry["gpt-4o"]["fingerprint_count"] == PROBE_COUNT


def test_fingerprints_are_merkle_chained():
    fps.generate_fingerprints("model-a", "openai", CORRECT_RESPONSES)
    first_head = fps._chain_head
    fps.generate_fingerprints("model-b", "anthropic", CORRECT_RESPONSES)
    second_head = fps._chain_head
    assert first_head != second_head


def test_verify_model_passes_with_matching_responses():
    fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    result = fps.verify_model("gpt-4o", CORRECT_RESPONSES)
    assert result.verified is True
    assert result.passed == PROBE_COUNT
    assert result.failed == 0
    assert result.pass_rate == 1.0


def test_verify_model_fails_with_wrong_responses():
    fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    result = fps.verify_model("gpt-4o", WRONG_RESPONSES)
    assert result.verified is False
    assert result.failed == PROBE_COUNT
    assert result.pass_rate == 0.0


def test_verify_unregistered_model_returns_not_registered():
    result = fps.verify_model("unknown-model", CORRECT_RESPONSES)
    assert result.verified is False
    assert result.total_challenges == 0


def test_audit_log_grows_after_events():
    fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    before = len(fps.get_audit_log())
    fps.verify_model("gpt-4o", CORRECT_RESPONSES)
    after = len(fps.get_audit_log())
    assert after == before + 1


def test_audit_log_is_merkle_chained():
    fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    fps.verify_model("gpt-4o", CORRECT_RESPONSES)
    fps.verify_model("gpt-4o", WRONG_RESPONSES)
    log = fps.get_audit_log()
    assert len(log) == 2
    assert log[1]["prev_hash"] == log[0]["chain_hash"]


def test_verification_updates_registry_status():
    fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    assert fps._registry["gpt-4o"].verification_status == "unverified"
    fps.verify_model("gpt-4o", CORRECT_RESPONSES)
    assert fps._registry["gpt-4o"].verification_status == "verified"


def test_tampered_model_marked_in_registry():
    fps.generate_fingerprints("gpt-4o", "openai", CORRECT_RESPONSES)
    fps.verify_model("gpt-4o", WRONG_RESPONSES)
    assert fps._registry["gpt-4o"].verification_status == "tampered"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_probes_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/fingerprint/probes")
    assert response.status_code == 200
    data = response.json()
    assert "probes" in data
    assert data["count"] == PROBE_COUNT
    assert "SA.L2-3.14.7" in data["cmmc_controls"]


@pytest.mark.anyio
async def test_register_endpoint_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/fingerprint/register",
            json={
                "model_id": "gpt-4o",
                "provider": "openai",
                "probe_responses": CORRECT_RESPONSES,
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["model_id"] == "gpt-4o"
    assert data["fingerprint_count"] == PROBE_COUNT
    assert "chain_hash" in data
    assert "SA.L2-3.14.7" in data["cmmc_controls"]


@pytest.mark.anyio
async def test_register_endpoint_rejects_insufficient_responses():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/fingerprint/register",
            json={
                "model_id": "gpt-4o",
                "provider": "openai",
                "probe_responses": ["only one response"],
            },
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_verify_endpoint_passes_correct_responses():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Register first
        await ac.post(
            "/api/fingerprint/register",
            json={
                "model_id": "gpt-4o",
                "provider": "openai",
                "probe_responses": CORRECT_RESPONSES,
            },
        )
        # Then verify
        response = await ac.post(
            "/api/fingerprint/verify",
            json={
                "model_id": "gpt-4o",
                "probe_responses": CORRECT_RESPONSES,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["pass_rate"] == 1.0
    assert "audit_chain_id" in data


@pytest.mark.anyio
async def test_verify_endpoint_fails_wrong_responses():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/api/fingerprint/register",
            json={
                "model_id": "gpt-4o",
                "provider": "openai",
                "probe_responses": CORRECT_RESPONSES,
            },
        )
        response = await ac.post(
            "/api/fingerprint/verify",
            json={
                "model_id": "gpt-4o",
                "probe_responses": WRONG_RESPONSES,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is False
    assert data["pass_rate"] == 0.0


@pytest.mark.anyio
async def test_registry_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/api/fingerprint/register",
            json={
                "model_id": "claude-opus",
                "provider": "anthropic",
                "probe_responses": CORRECT_RESPONSES,
            },
        )
        response = await ac.get("/api/fingerprint/registry")
    assert response.status_code == 200
    data = response.json()
    assert "claude-opus" in data["registered_models"]
    assert data["count"] >= 1


@pytest.mark.anyio
async def test_audit_log_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/api/fingerprint/register",
            json={
                "model_id": "gpt-4o",
                "provider": "openai",
                "probe_responses": CORRECT_RESPONSES,
            },
        )
        await ac.post(
            "/api/fingerprint/verify",
            json={
                "model_id": "gpt-4o",
                "probe_responses": CORRECT_RESPONSES,
            },
        )
        response = await ac.get("/api/fingerprint/audit")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    # Verify Merkle chain integrity in the log
    log = data["audit_log"]
    if len(log) >= 2:
        assert log[1]["prev_hash"] == log[0]["chain_hash"]
    assert "SI.L1-3.14.1" in data["cmmc_controls"]
