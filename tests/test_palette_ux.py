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


@pytest.mark.anyio
async def test_zt_pillar_progress_accuracy():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        content = resp.text

        # Verify ZT Pillar Alignment section headers
        assert "| ZT Pillar | CMMC Domains | Progress |" in content

        # Verify specific pillars are present
        assert "| User | AC, IA, PS |" in content
        assert "| Device | CM, MA, PE |" in content

        # In our setup_db:
        # AC.1.001 is implemented (100%)
        # AC.1.002 is partial (50%)
        # User pillar domains: AC, IA, PS.
        # Only AC domains have assessments.
        # AC.1.001 and AC.1.002 both start with AC.
        # Maturity for User pillar should be (1.0 + 0.5) / 2 = 75%
        # get_progress_bar(75) with width 10: filled = round(0.75 * 10) = 8
        # Resulting bar: `████████░░` 75.0%
        assert "`████████░░` 75.0%" in content


@pytest.mark.anyio
async def test_dashboard_zt_consistency():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        # Check for ZT pillars in dashboard
        zt_pillars = data.get("zt_pillars", [])
        assert len(zt_pillars) == 7

        # Find User pillar
        user_pillar = next((p for p in zt_pillars if p["pillar"] == "User"), None)
        assert user_pillar is not None
        assert user_pillar["maturity"] == 75.0
