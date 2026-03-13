
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base
import os

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_val.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_val.db"):
        os.remove("./test_val.db")

@pytest.mark.anyio
async def test_control_update_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test invalid confidence (> 1.0)
        payload = {
            "implementation_status": "implemented",
            "confidence": 5.0
        }
        response = await ac.patch("/api/controls/AC.1.001", json=payload)
        # Currently this might pass because validation is missing
        # We WANT it to fail (422 Unprocessable Entity)
        assert response.status_code == 422, f"Should have failed with 422, got {response.status_code}"

@pytest.mark.anyio
async def test_control_update_validation_negative():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test invalid confidence (< 0.0)
        payload = {
            "implementation_status": "implemented",
            "confidence": -0.5
        }
        response = await ac.patch("/api/controls/AC.1.001", json=payload)
        assert response.status_code == 422

@pytest.mark.anyio
async def test_promote_agent_run_validation():
    from backend.db.database import AgentRunRecord, AsyncSessionLocal
    import uuid
    from datetime import datetime, UTC

    async with AsyncSessionLocal() as session:
        # Create a mock agent run with invalid data
        run_id = str(uuid.uuid4())
        mock_run = AgentRunRecord(
            id=run_id,
            agent_type="icam",
            findings={
                "results": [
                    {
                        "control_id": "AC.1.001",
                        "status": "invalid_status",
                        "confidence": 1.5,
                        "findings": ["Test findings"],
                        "evidence_id": "ev-1"
                    }
                ]
            },
            status="completed",
            created_at=datetime.now(UTC)
        )
        session.add(mock_run)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/api/assessment/promote/{run_id}")
        assert response.status_code == 200

        # Verify that the promoted assessment has clamped/validated values
        response = await ac.get("/api/controls/AC.1.001")
        assert response.status_code == 200
        data = response.json()
        # invalid_status should have defaulted to not_started
        assert data["implementation_status"] == "not_started"
        # 1.5 confidence should have been clamped to 1.0
        assert data["confidence"] == 1.0
