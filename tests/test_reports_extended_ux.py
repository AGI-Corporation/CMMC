import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import (AssessmentRecord, Base, ControlRecord, engine,
                                 init_db)
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    import os

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_extended_ux.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()

    from backend.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Check if control already exists (init_db might seed it)
        from sqlalchemy import select

        res = await session.execute(
            select(ControlRecord).where(ControlRecord.id == "AC.1.001")
        )
        if not res.scalars().first():
            c1 = ControlRecord(
                id="AC.1.001",
                domain="AC",
                level="Level 1",
                title="Limit system access",
                description="Limit system access to authorized users",
            )
            session.add(c1)

        # Add assessments with new statuses
        a1 = AssessmentRecord(
            id=str(uuid.uuid4()),
            control_id="AC.1.001",
            status="in_progress",
            confidence=0.0,
            assessment_date=datetime.now(UTC),
        )
        a2 = AssessmentRecord(
            id=str(uuid.uuid4()),
            control_id="AC.1.002",
            status="not_applicable",
            confidence=0.8,
            assessment_date=datetime.now(UTC),
        )
        session.add_all([a1, a2])
        await session.commit()

    yield
    if os.path.exists("./test_extended_ux.db"):
        os.remove("./test_extended_ux.db")


@pytest.mark.anyio
async def test_extended_report_ux():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        content = resp.text

        # Check for new status emojis
        assert "🟡 In Progress" in content or "🟡" in content
        assert "⚪ Not Applicable" in content or "⚪" in content

        # Check for 0-star rating
        assert "☆☆☆☆☆" in content

        # Check for "Showing X of Y" metadata
        assert "Showing" in content
        assert "assessment findings" in content

        # Check for "Back to Top" links
        assert "[Back to Top](#system-security-plan-ssp)" in content


@pytest.mark.anyio
async def test_dashboard_consistency():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        # in_progress should be in 'partial' count
        assert data["status_breakdown"]["partial"] >= 1
        # not_applicable should be in 'na' count
        assert data["status_breakdown"]["na"] >= 1
