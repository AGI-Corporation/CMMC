
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
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_palette.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_palette.db"):
        os.remove("./test_palette.db")

@pytest.mark.anyio
async def test_ssp_report_visuals():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Update a control to have some assessment data
        update_data = {
            "implementation_status": "implemented",
            "notes": "Test implemented",
            "confidence": 0.8
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # 2. Update another to partial
        update_data = {
            "implementation_status": "partially_implemented",
            "notes": "Test partial",
            "confidence": 0.5
        }
        await ac.patch("/api/controls/AC.1.002", json=update_data)

        # 3. Get SSP report
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        content = resp.text

        # Verify visual enhancements
        assert "✅" in content
        assert "🟡" in content
        assert "█" in content  # Progress bar character
        assert "░" in content  # Progress bar character
        assert "⭐" in content
        assert "Overall Compliance:" in content
        assert "🏢" in content
        assert "🔒" in content
