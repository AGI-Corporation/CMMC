
import pytest
import os
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agents.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_agents.db"):
        os.remove("./test_agents.db")

@pytest.mark.anyio
async def test_icam_assess():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/agents/icam/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "icam"
    assert len(data["assessments"]) > 0

@pytest.mark.anyio
async def test_devsecops_assess():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/agents/devsecops/assess/test-service")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "devsecops"
    assert "image_scan" in data

@pytest.mark.anyio
async def test_orchestrator_scorecard():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/orchestrator/scorecard")
    assert response.status_code == 200
    data = response.json()
    assert "scorecard" in data
    assert "sprs" in data

@pytest.mark.anyio
async def test_mistral_gap_analysis_mock():
    # Mistral API key is likely missing in tests, so it should return mock response
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        req = {
            "control_id": "AC.1.001",
            "control_title": "Limit access",
            "control_description": "Desc",
            "zt_pillar": "User"
        }
        response = await ac.post("/api/agents/mistral/gap-analysis", json=req)
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    # If API key is missing, it should have our mock summary
    if not os.getenv("MISTRAL_API_KEY"):
        assert "Mock analysis" in data["analysis"]["gap_summary"]
