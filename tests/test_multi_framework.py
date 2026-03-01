
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db

@pytest.mark.asyncio
async def test_multi_framework_seeding():
    # init_db is called during lifespan, but we can verify results
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test CMMC
        response = await ac.get("/api/controls/?framework=CMMC")
        assert response.status_code == 200
        assert response.json()["total"] == 11

        # Test NIST
        response = await ac.get("/api/controls/?framework=NIST")
        assert response.status_code == 200
        assert response.json()["total"] == 3

        # Test HIPAA
        response = await ac.get("/api/controls/?framework=HIPAA")
        assert response.status_code == 200
        assert response.json()["total"] == 3

        # Test FHIR
        response = await ac.get("/api/controls/?framework=FHIR")
        assert response.status_code == 200
        assert response.json()["total"] == 2

@pytest.mark.asyncio
async def test_multi_framework_orchestrator_run():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Run NIST assessment
        response = await ac.post("/api/orchestrator/run?framework=NIST")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "NIST" in data["ai_summary"] or "assessment" in data["ai_summary"].lower() or "mistral" in data["ai_summary"].lower()

        # Verify NIST scorecard
        response = await ac.get("/api/orchestrator/scorecard?framework=NIST")
        assert response.status_code == 200
        assert response.json()["sprs"]["controls_assessed"] == 3

@pytest.mark.asyncio
async def test_nanda_registry_new_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/nanda/")
        assert response.status_code == 200
        agents = response.json()["agents"]
        agent_ids = [a["agent_id"] for a in agents]
        assert "nist-01" in agent_ids
        assert "hipaa-01" in agent_ids
        assert "fhir-01" in agent_ids
