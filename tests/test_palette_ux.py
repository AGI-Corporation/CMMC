
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
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_ux.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_ux.db"):
        os.remove("./test_ux.db")

@pytest.mark.anyio
async def test_ssp_visual_elements():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Seed some data if necessary (already seeded by init_db)

        # Check SSP report
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        content = resp.text

        # Verify visual progress bar
        assert "Overall Progress:" in content
        assert "█" in content or "░" in content

        # Verify status emojis
        assert "✅" in content or "🟡" in content or "📝" in content or "🛑" in content or "⚪" in content

        # Verify confidence stars
        # Note: Depending on seeded data, stars might not appear if assessments list is empty.
        # But init_db seeds controls, not necessarily assessments.
        # Let's add an assessment to be sure.

        # 1. Update a control to implemented
        update_data = {
            "implementation_status": "implemented",
            "notes": "Palette UX Test",
            "responsible_party": "Palette",
            "confidence": 0.8
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # 2. Check SSP again
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        content = resp.text

        # Now stars and implemented emoji should definitely be there
        assert "✅" in content
        assert "⭐" in content
        assert "Palette UX Enhanced" in content
