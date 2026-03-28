
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base
import os

@pytest.fixture(scope="module")
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_palette.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_palette.db"):
        os.remove("./test_palette.db")

@pytest.mark.anyio
async def test_ssp_ux_enhanced(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Update a control to have some status and confidence
        update_data = {
            "implementation_status": "implemented",
            "notes": "Verified implementation",
            "responsible_party": "Palette",
            "confidence": 1.0
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # 2. Generate SSP
        response = await ac.get("/api/reports/ssp")

    assert response.status_code == 200
    print("\n--- Enhanced SSP Output ---")
    print(response.text)
    print("----------------------------")

    # Check for emojis
    assert "✅" in response.text
    # Check for progress bar
    assert "█" in response.text or "░" in response.text
    # Check for confidence stars
    assert "⭐⭐⭐⭐⭐" in response.text
