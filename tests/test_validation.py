import pytest
import os
import uuid
from datetime import datetime, UTC
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base, AgentRunRecord, AssessmentRecord
from sqlalchemy import select

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
async def test_confidence_range_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test confidence > 1.0
        update_data = {
            "implementation_status": "implemented",
            "confidence": 1.5
        }
        response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert response.status_code == 422

        # Test confidence < 0.0
        update_data["confidence"] = -0.1
        response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert response.status_code == 422

        # Test valid confidence
        update_data["confidence"] = 0.5
        response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert response.status_code == 200

@pytest.mark.anyio
async def test_agent_findings_sanitization(setup_db):
    from backend.db.database import AsyncSessionLocal

    # Manually insert a "dirty" agent run
    run_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        record = AgentRunRecord(
            id=run_id,
            agent_type="icam",
            findings={
                "results": [
                    {
                        "control_id": "AC.1.001",
                        "status": "partial", # should be mapped to partially_implemented
                        "confidence": 1.2,    # should be clamped to 1.0
                        "findings": ["Test"],
                        "evidence_id": "ev-1"
                    }
                ]
            },
            status="completed"
        )
        session.add(record)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/api/assessment/promote/{run_id}")
        assert response.status_code == 200

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AssessmentRecord).where(AssessmentRecord.control_id == "AC.1.001")
            .order_by(AssessmentRecord.assessment_date.desc())
        )
        assessment = result.scalars().first()
        assert assessment.status == "partially_implemented"
        assert assessment.confidence == 1.0
