import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_ops_agent_direct():
    """Test Ops Agent endpoints directly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/agents/ops/run?trigger=manual")
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "ops-01"
        assert len(data["findings"]) > 0
        assert any(f["control_id"] == "AU.2.041" for f in data["findings"])

@pytest.mark.asyncio
async def test_governance_agent_direct():
    """Test Governance Agent endpoints directly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/agents/governance/run?trigger=manual")
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "gov-01"
        assert len(data["findings"]) > 0
        assert any(f["control_id"] == "CA.2.158" for f in data["findings"])

@pytest.mark.asyncio
async def test_orchestrator_integration_ops_gov():
    """Test that Orchestrator includes new agents in full CMMC run."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Trigger full run
        response = await ac.post("/api/orchestrator/run?framework=CMMC")
        assert response.status_code == 200
        run_data = response.json()
        run_id = run_data["run_id"]

        # Verify in NANDA registry
        registry_res = await ac.get("/api/nanda/")
        registry_data = registry_res.json()
        agent_names = [a["name"] for a in registry_data["agents"]]
        assert "Operational Security Agent" in agent_names
        assert "Governance & Risk Agent" in agent_names
