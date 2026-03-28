import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import AssessmentRecord, Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    # Use a separate test database for this module
    import os

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_ux.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()

    # Add some sample assessments with different confidence/status
    from backend.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        a1 = AssessmentRecord(
            id=str(uuid.uuid4()),
            control_id="AC.1.001",
            status="implemented",
            confidence=1.0,
            assessment_date=datetime.now(UTC),
        )
        a2 = AssessmentRecord(
            id=str(uuid.uuid4()),
            control_id="AC.1.002",
            status="partial",
            confidence=0.5,
            assessment_date=datetime.now(UTC),
        )
        session.add_all([a1, a2])
        await session.commit()

    yield
    # Cleanup
    if os.path.exists("./test_ux.db"):
        os.remove("./test_ux.db")


@pytest.mark.anyio
async def test_ssp_ux_elements():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        content = resp.text

        # Check for progress bar characters
        assert "█" in content or "░" in content
        assert "Overall Compliance" in content

        # Check for emojis
        assert "✅" in content
        assert "🟡" in content

        # Check for confidence stars
        # 1.0 confidence should have 5 stars: ⭐⭐⭐⭐⭐
        assert "⭐⭐⭐⭐⭐" in content
        # 0.5 confidence should have 3 stars: ⭐⭐⭐☆☆ (based on int(0.5 * 5 + 0.5) = 3)
        assert "⭐⭐⭐☆☆" in content
