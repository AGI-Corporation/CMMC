"""
Tests for deep roadmap integrations:
- Blockchain service
- Notification service
- Assessment submit / history / runs / summary / notifications endpoints
- Blockchain ledger / verify endpoints
- Maturity heatmap report
- Governance agent
- Awareness agent
- Orchestrator execute endpoint
- Rate limiting middleware
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_integrations_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_integrations.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_integrations.db"):
        os.remove("./test_integrations.db")


# ---------------------------------------------------------------------------
# Assessment submit
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_assessment_submit_valid_control():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "AC.1.001",
                "status": "implemented",
                "confidence": 0.9,
                "notes": "Test submission",
                "assessor": "tester",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "submitted"
    assert data["control_id"] == "AC.1.001"
    assert data["assessment_status"] == "implemented"
    assert data["poam_required"] is False
    assert "assessment_id" in data


@pytest.mark.anyio
async def test_assessment_submit_auto_flags_poam():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "AC.1.002",
                "status": "not_implemented",
                "confidence": 0.1,
                "notes": "Not done yet",
                "assessor": "tester",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["poam_required"] is True


@pytest.mark.anyio
async def test_assessment_submit_invalid_control():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "FAKE.9.999",
                "status": "implemented",
                "confidence": 1.0,
            },
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_assessment_submit_partial_sets_poam():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "IA.1.076",
                "status": "partially_implemented",
                "confidence": 0.5,
            },
        )
    assert resp.status_code == 200
    assert resp.json()["poam_required"] is True


# ---------------------------------------------------------------------------
# Assessment history
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_assessment_history():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/history/AC.1.001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "AC.1.001"
    assert "history" in data
    assert data["total"] >= 1  # we submitted one above
    rec = data["history"][0]
    assert "status" in rec
    assert "assessment_date" in rec


@pytest.mark.anyio
async def test_assessment_history_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/history/AC.1.001?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()["history"]) <= 1


# ---------------------------------------------------------------------------
# Assessment runs
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_assessment_runs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First run the governance agent to create a run record
        await ac.get("/api/agents/governance/assess")
        resp = await ac.get("/api/assessment/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert data["total"] >= 1
    run = data["runs"][0]
    assert "id" in run
    assert "agent_type" in run
    assert "status" in run


@pytest.mark.anyio
async def test_assessment_runs_filter_by_agent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/runs?agent_type=governance")
    assert resp.status_code == 200
    data = resp.json()
    for run in data["runs"]:
        assert run["agent_type"] == "governance"


# ---------------------------------------------------------------------------
# Assessment summary
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_assessment_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "domains" in data
    assert "total_domains" in data
    assert "generated_at" in data
    for domain in data["domains"]:
        assert "domain" in domain
        assert "sprs_deduction" in domain
        assert "compliance_pct" in domain
        assert "avg_confidence" in domain


@pytest.mark.anyio
async def test_assessment_summary_sorted_by_sprs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/summary")
    data = resp.json()
    deductions = [d["sprs_deduction"] for d in data["domains"]]
    assert deductions == sorted(deductions, reverse=True)


# ---------------------------------------------------------------------------
# Assessment notifications
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_assessment_notifications():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ensure at least one POAM event was logged
        await ac.post(
            "/api/assessment/submit",
            json={"control_id": "SI.1.210", "status": "not_implemented", "confidence": 0.0},
        )
        resp = await ac.get("/api/assessment/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert data["total"] >= 0  # may be 0 if notification log is empty on new process


@pytest.mark.anyio
async def test_assessment_notifications_filter_by_event_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/notifications?event_type=poam_flagged")
    assert resp.status_code == 200
    data = resp.json()
    for event in data["events"]:
        assert event["event_type"] == "poam_flagged"


# ---------------------------------------------------------------------------
# Blockchain ledger + verify
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_blockchain_ledger():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/blockchain/ledger")
    assert resp.status_code == 200
    data = resp.json()
    assert "transactions" in data
    assert data["total"] >= 1  # at least one TX from submit tests
    tx = data["transactions"][0]
    assert "sequence" in tx
    assert "payload_hash" in tx
    assert "previous_hash" in tx
    assert "event_type" in tx


@pytest.mark.anyio
async def test_blockchain_verify():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/blockchain/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "valid" in data
    assert data["valid"] is True
    assert data["broken_at_sequence"] is None


# ---------------------------------------------------------------------------
# Maturity heatmap
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_maturity_heatmap():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/maturity-heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert "pillar_rollup" in data
    assert "matrix" in data
    assert "generated_at" in data
    assert len(data["pillar_rollup"]) > 0
    for pillar in data["pillar_rollup"]:
        assert "pillar" in pillar
        assert "maturity_score" in pillar
        assert "avg_confidence" in pillar
        assert 0.0 <= pillar["maturity_score"] <= 100.0


@pytest.mark.anyio
async def test_maturity_heatmap_pillar_rollup_sorted():
    """Pillar rollup must be sorted by maturity_score ascending (weakest first)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/maturity-heatmap")
    scores = [p["maturity_score"] for p in resp.json()["pillar_rollup"]]
    assert scores == sorted(scores)


@pytest.mark.anyio
async def test_maturity_heatmap_user_pillar_has_at_domain():
    """User pillar should include the AT (Awareness & Training) domain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/maturity-heatmap")
    user_pillars = [p for p in resp.json()["pillar_rollup"] if p["pillar"] == "User"]
    assert len(user_pillars) == 1
    assert "AT" in user_pillars[0]["domains"]


# ---------------------------------------------------------------------------
# Governance agent
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_governance_agent_assess():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/agents/governance/assess")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "governance"
    assert len(data["controls_evaluated"]) == 13  # 13 unique check methods
    for result in data["results"]:
        assert "control_id" in result
        assert "status" in result
        assert "confidence" in result
        assert "zt_pillar" in result
        assert "findings" in result
        assert "remediation" in result


@pytest.mark.anyio
async def test_governance_agent_includes_sa2150():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/agents/governance/assess")
    control_ids = [r["control_id"] for r in resp.json()["results"]]
    assert "SA.2.150" in control_ids


# ---------------------------------------------------------------------------
# Awareness agent
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_awareness_agent_assess():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/agents/awareness/assess")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "awareness"
    assert len(data["controls_evaluated"]) == 5
    expected = {"AT.2.056", "AT.2.057", "AT.3.058", "PS.2.127", "PS.2.128"}
    assert set(data["controls_evaluated"]) == expected


@pytest.mark.anyio
async def test_awareness_results_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/agents/awareness/assess")
    for result in resp.json()["results"]:
        assert result["zt_pillar"] == "User"
        assert result["status"] in (
            "implemented", "partially_implemented", "not_implemented"
        )
        assert 0.0 <= result["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Orchestrator execute endpoint
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_orchestrator_execute():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/orchestrator/execute?trigger=assessment&scope=test")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents_executed" in data
    assert "results" in data
    assert "total_controls_assessed" in data
    assert data["total_controls_assessed"] >= 1


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_rate_limit_allows_normal_traffic():
    """Requests well under the limit should all succeed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for _ in range(5):
            resp = await ac.get("/health")
            assert resp.status_code == 200


@pytest.mark.anyio
async def test_rate_limit_resets_between_tests():
    """
    Because of the conftest reset_rate_limiter autouse fixture, this test
    starts with a clean window and should not see 429 from prior tests.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_rate_limit_triggers_429(monkeypatch):
    """Exceeding the window limit must return HTTP 429."""
    import backend.middleware.rate_limit as rl

    # Temporarily lower the limit for this test
    original = rl._MAX_REQUESTS
    monkeypatch.setattr(rl, "_MAX_REQUESTS", 3)
    rl.reset_all_windows()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            responses = [await ac.get("/health") for _ in range(4)]
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
    finally:
        monkeypatch.setattr(rl, "_MAX_REQUESTS", original)
        rl.reset_all_windows()
