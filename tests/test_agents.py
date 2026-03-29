import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import AsyncSessionLocal, Base, engine, init_db
from backend.main import app


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
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/icam/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "icam"
    assert len(data["assessments"]) > 0


@pytest.mark.anyio
async def test_devsecops_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/devsecops/assess/test-service")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "devsecops"
    assert "image_scan" in data


@pytest.mark.anyio
async def test_orchestrator_scorecard():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/orchestrator/scorecard")
    assert response.status_code == 200
    data = response.json()
    assert "scorecard" in data
    assert "sprs" in data


@pytest.mark.anyio
async def test_mistral_gap_analysis_mock():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        req = {
            "control_id": "AC.1.001",
            "control_title": "Limit access",
            "control_description": "Desc",
            "zt_pillar": "User",
        }
        response = await ac.post("/api/agents/mistral/gap-analysis", json=req)
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    if not os.getenv("MISTRAL_API_KEY"):
        assert "Mock analysis" in data["analysis"]["gap_summary"]


@pytest.mark.anyio
async def test_agent_run_promotion():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Trigger an agent run (ICAM)
        assess_resp = await ac.get("/api/agents/icam/assess")
        assert assess_resp.status_code == 200

        # 2. Get the run ID from the database
        from sqlalchemy import select

        from backend.db.database import AgentRunRecord

        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(AgentRunRecord).order_by(AgentRunRecord.created_at.desc())
            )
            run = res.scalars().first()
            run_id = run.id

        # 3. Promote the run
        promote_resp = await ac.post(f"/api/assessment/promote/{run_id}")
        assert promote_resp.status_code == 200
        assert promote_resp.json()["status"] == "promoted"
        assert promote_resp.json()["assessments_created"] > 0

        # 4. Verify assessment exists for one of the controls
        # ICAM evaluates IA.3.083
        detail_resp = await ac.get("/api/controls/IA.3.083")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert data["implementation_status"] == "partially_implemented"
        assert "Promoted from icam" in data["notes"]
