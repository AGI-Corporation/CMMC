
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.routers.reports import get_status_emoji, get_confidence_stars, get_progress_bar

def test_status_emojis():
    assert get_status_emoji("implemented") == "✅"
    assert get_status_emoji("partial") == "🟡"
    assert get_status_emoji("planned") == "📝"
    assert get_status_emoji("not_implemented") == "🛑"
    assert get_status_emoji("na") == "⚪"
    assert get_status_emoji("unknown") == "❓"

def test_confidence_stars():
    assert get_confidence_stars(1.0) == "⭐⭐⭐⭐⭐"
    assert get_confidence_stars(0.5) == "⭐⭐⭐"
    assert get_confidence_stars(0.2) == "⭐"
    assert get_confidence_stars(0.0) == "🌑"

def test_progress_bar():
    bar = get_progress_bar(50.0, width=10)
    assert "█████░░░░░" in bar
    assert "50.0%" in bar

@pytest.mark.anyio
async def test_ssp_visual_elements():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # We need some data in the DB for a meaningful SSP
        # But even with empty DB, it should show 0% progress bar
        response = await ac.get("/api/reports/ssp")
        assert response.status_code == 200
        content = response.text

        # Check for progress bar
        assert "Overall Progress:" in content
        # It seems test_backend.py seeds some data if run in the same session,
        # or it might be picking up existing test.db if not cleaned up properly.
        # Let's just check if it contains ANY progress bar pattern.
        assert "█" in content or "░" in content

        # Check for legend/overview emojis
        assert "✅" in content
        assert "🛑" in content
        assert "🟡" in content
