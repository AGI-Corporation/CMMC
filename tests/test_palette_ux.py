import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base
import os

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_palette.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_palette.db"):
        os.remove("./test_palette.db")

@pytest.mark.anyio
async def test_ssp_report_ux_elements():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Update a control to 'implemented' so we have something to see
        update_data = {
            "implementation_status": "implemented",
            "notes": "Palette test",
            "responsible_party": "Palette",
            "confidence": 1.0
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # 2. Get the SSP report
        response = await ac.get("/api/reports/ssp")
        assert response.status_code == 200
        content = response.text

        # 3. Verify UX elements are present
        assert "Overall Progress" in content
        assert "█" in content or "░" in content  # Progress bar characters
        assert "✅" in content  # Status emoji for implemented
        assert "⭐⭐⭐" in content  # Confidence stars for 1.0 confidence
