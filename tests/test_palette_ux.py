import pytest
import os
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base
from backend.routers.reports import get_status_emoji, get_progress_bar, get_confidence_stars

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module")
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

def test_get_status_emoji():
    assert get_status_emoji("implemented") == "✅"
    assert get_status_emoji("partial") == "🟡"
    assert get_status_emoji("partially_implemented") == "🟡"
    assert get_status_emoji("planned") == "📝"
    assert get_status_emoji("not_implemented") == "🛑"
    assert get_status_emoji("na") == "⚪"
    assert get_status_emoji("unknown") == "⚪"

def test_get_progress_bar():
    bar_50 = get_progress_bar(50, width=10)
    assert "█████░░░░░" in bar_50
    assert "50.0%" in bar_50

    bar_100 = get_progress_bar(100, width=10)
    assert "██████████" in bar_100
    assert "100.0%" in bar_100

def test_get_confidence_stars():
    assert get_confidence_stars(1.0) == "⭐⭐⭐⭐⭐"
    assert get_confidence_stars(0.8) == "⭐⭐⭐⭐"
    assert get_confidence_stars(0.6) == "⭐⭐⭐"
    assert get_confidence_stars(0.5) == "⭐⭐⭐" # Standard rounding: 0.5 * 5 + 0.5 = 3.0 -> 3 stars
    assert get_confidence_stars(0.4) == "⭐⭐"
    assert get_confidence_stars(0.2) == "⭐"
    assert get_confidence_stars(0.0) == "No Stars"

@pytest.mark.anyio
async def test_ssp_endpoint_visuals(setup_db):
    """
    Test that the SSP endpoint returns the new visual elements.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Update AC.1.001 to implemented to ensure we have something in the report
        update_data = {
            "implementation_status": "implemented",
            "notes": "Test fix",
            "responsible_party": "Tester",
            "confidence": 0.9
        }
        await ac.patch("/api/controls/AC.1.001", json=update_data)

        # 2. Check SSP
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        content = resp.text

        # Check for progress bar characters
        assert "█" in content or "░" in content
        assert "Overall Compliance" in content

        # Check for emojis and stars (since we updated AC.1.001)
        assert "✅" in content
        assert "⭐⭐⭐⭐⭐" in content
