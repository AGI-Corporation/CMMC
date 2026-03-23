
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
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_palette.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_palette.db"):
        os.remove("./test_palette.db")

@pytest.mark.anyio
async def test_ssp_report_ux_elements():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First update a control to 'implemented' so we have some progress
        update_data = {
            "implementation_status": "implemented",
            "notes": "Palette UX test",
            "responsible_party": "Palette",
            "confidence": 0.8
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # Generate SSP report
        response = await ac.get("/api/reports/ssp")
        assert response.status_code == 200
        content = response.text

        # 1. Check for Status Emojis
        assert "✅ Implemented" in content
        assert "🛑 Not Implemented" in content

        # 2. Check for Progress Bar (█ and ░ characters)
        assert "█" in content
        assert "░" in content
        assert "Overall Compliance" in content

        # 3. Check for Confidence Stars (⭐)
        assert "⭐" in content
        assert "Confidence:" in content
        # With 0.8 confidence, it should have 4 stars (int(0.8 * 5 + 0.5) = 4)
        assert "⭐⭐⭐⭐" in content
