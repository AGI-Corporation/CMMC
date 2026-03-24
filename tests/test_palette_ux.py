
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
        # 1. Update a control to ensure we have an assessment finding to check
        update_data = {
            "implementation_status": "implemented",
            "notes": "Palette UX Test",
            "confidence": 0.8
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # 2. Generate SSP report
        response = await ac.get("/api/reports/ssp")
        assert response.status_code == 200
        content = response.text

        # 3. Verify visual elements
        # Progress bar characters
        assert "█" in content or "░" in content
        # Status emojis
        assert "✅" in content
        # Confidence stars
        assert "⭐" in content

        # Verify specific formatting for AC.1.001
        assert "### AC.1.001" in content
        assert "- **Status:** ✅ implemented" in content
        # 0.8 * 5 = 4 stars
        assert "- **Confidence:** ⭐⭐⭐⭐ (80%)" in content

        # Verify System Overview table has emojis
        assert "| Implemented | ✅" in content
