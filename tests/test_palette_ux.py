
import pytest
import os
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base, ControlRecord, AssessmentRecord, AsyncSessionLocal
import uuid
from datetime import datetime, UTC

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_ux.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()

    # Seed specific data for UX testing
    async with AsyncSessionLocal() as session:
        # We assume some controls are already seeded by init_db() from the catalog
        # Let's add some assessments with specific confidence and status
        assessments = [
            AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id="AC.1.001",
                status="implemented",
                confidence=1.0,
                assessment_date=datetime.now(UTC)
            ),
            AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id="AC.1.002",
                status="partial",
                confidence=0.5,
                assessment_date=datetime.now(UTC)
            ),
            AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id="IA.1.001",
                status="not_implemented",
                confidence=0.2,
                assessment_date=datetime.now(UTC)
            )
        ]
        session.add_all(assessments)
        await session.commit()

    yield
    # Cleanup
    if os.path.exists("./test_ux.db"):
        os.remove("./test_ux.db")

@pytest.mark.anyio
async def test_ssp_ux_elements():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        text = resp.text

        # Check for progress bar elements
        assert "Overall Compliance:" in text
        assert "█" in text or "░" in text

        # Check for status emojis in the overview table
        assert "✅" in text
        assert "🟡" in text
        assert "🛑" in text

        # Check for stars in assessment findings
        assert "⭐⭐⭐⭐⭐" in text  # for 1.0 confidence
        assert "⭐⭐⭐" in text      # for 0.5 confidence
        assert "⭐" in text        # for 0.2 confidence

        # Check that emojis are next to statuses
        assert "implemented ✅" in text or "✅ implemented" in text or "Status:** implemented ✅" in text
