
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
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_palette_ux.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_palette_ux.db"):
        os.remove("./test_palette_ux.db")

@pytest.mark.anyio
async def test_ssp_report_ux_elements():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Update a control to ensure we have an assessment with confidence
        update_data = {
            "implementation_status": "implemented",
            "notes": "Palette UX test",
            "responsible_party": "Palette",
            "confidence": 0.8,
            "evidence_ids": ["ev-ux-1"]
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # 2. Generate SSP report
        response = await ac.get("/api/reports/ssp")
        assert response.status_code == 200
        content = response.text

        # 3. Verify UX elements
        # Progress bar
        assert "Overall Compliance:" in content
        assert "█" in content or "░" in content

        # Status emojis in overview table
        assert "✅" in content
        assert "🟡" in content
        assert "🛑" in content

        # Findings section
        assert "### AC.1.001" in content
        assert "✅ implemented" in content
        assert "⭐" in content  # 0.8 confidence should be 4 stars
        assert "⭐⭐⭐⭐" in content
