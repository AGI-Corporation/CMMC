
import pytest
import httpx
import pytest_asyncio
from backend.main import app

@pytest.mark.asyncio
async def test_nanda_registry():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/nanda/")

    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) >= 5

    # Verify specific agent facts
    icam = next(a for a in data["agents"] if a["agent_id"] == "icam-01")
    assert icam["name"] == "ICAM Agent"
    assert "Access Control" in icam["capabilities"]
    assert icam["trust_level"] == "verified"

@pytest.mark.asyncio
async def test_oml_fingerprinting_on_run():
    # Trigger an agent run and check for fingerprint
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # We'll use the infra agent for a quick check
        response = await ac.get("/api/agents/infra/assess")
        assert response.status_code == 200

        # Verify it shows up in the orchestrator report (Integrity Feed source)
        report_res = await ac.get("/api/orchestrator/report")
        report_data = report_res.json()

        recent_run = next(r for r in report_data["agent_runs"] if r["agent"] == "infra")
        assert "fingerprint" in recent_run
        assert len(recent_run["fingerprint"]) == 64

@pytest.mark.asyncio
async def test_provenance_promotion():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a run
        run_res = await ac.get("/api/agents/icam/assess")
        assert run_res.status_code == 200

        # 2. Get real run ID from reports
        report_res = await ac.get("/api/orchestrator/report")
        run_record = next(r for r in report_res.json()["agent_runs"] if r["agent"] == "icam")
        run_id = run_record["id"]

        # 3. Promote it
        promo_res = await ac.post(f"/api/assessment/promote/{run_id}")
        assert promo_res.status_code == 200
        assert promo_res.json()["status"] == "promoted"
        assert promo_res.json()["assessments_created"] > 0
