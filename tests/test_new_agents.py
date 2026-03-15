
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
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_new_agents.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_new_agents.db"):
        os.remove("./test_new_agents.db")

@pytest.mark.anyio
async def test_infra_agent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/agents/infra/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "infra"
    # Verify SC.1.175 is evaluated
    control_ids = [f["control_id"] for f in data["findings"]]
    assert "SC.1.175" in control_ids
    assert data["zt_pillar"] == "Network"

@pytest.mark.anyio
async def test_data_agent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/agents/data/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "data"
    # Verify MP.1.118 is evaluated
    control_ids = [f["control_id"] for f in data["findings"]]
    assert "MP.1.118" in control_ids
    assert data["zt_pillar"] == "Data"

@pytest.mark.anyio
async def test_promotion_infra_data():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Run and Promote Infra
        infra_resp = await ac.get("/api/agents/infra/assess")
        # Run and Promote Data
        data_resp = await ac.get("/api/agents/data/assess")

        from backend.db.database import AsyncSessionLocal, AgentRunRecord
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            # Promote Infra
            res = await session.execute(select(AgentRunRecord).where(AgentRunRecord.agent_type == "infra"))
            infra_run = res.scalars().first()
            resp = await ac.post(f"/api/assessment/promote/{infra_run.id}")
            assert resp.json()["status"] == "promoted"

            # Promote Data
            res = await session.execute(select(AgentRunRecord).where(AgentRunRecord.agent_type == "data"))
            data_run = res.scalars().first()
            resp = await ac.post(f"/api/assessment/promote/{data_run.id}")
            assert resp.json()["status"] == "promoted"

        # Verify dashboard reflects it
        dash_resp = await ac.get("/api/assessment/dashboard")
        dash = dash_resp.json()
        assert dash["by_domain"]["SC"]["implemented"] > 0
        assert dash["by_domain"]["MP"]["implemented"] > 0
