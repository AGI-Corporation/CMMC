
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
async def test_ssp_visual_elements():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First, ensure there's at least one assessment with confidence to test stars
        update_data = {
            "implementation_status": "implemented",
            "notes": "Palette Test",
            "responsible_party": "Palette",
            "confidence": 0.8
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # Generate SSP
        response = await ac.get("/api/reports/ssp")
        assert response.status_code == 200
        content = response.text

        # 1. Check for Progress Bar characters
        assert "█" in content or "░" in content

        # 2. Check for Status Emojis
        assert "✅" in content

        # 3. Check for Confidence Stars
        # 0.8 confidence should result in 4 stars
        assert "⭐⭐⭐⭐" in content

        # 4. Check for progress percentage
        assert "%" in content
