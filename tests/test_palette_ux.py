import pytest
from httpx import AsyncClient
from backend.main import app
from backend.routers.reports import get_status_emoji, get_progress_bar, get_confidence_stars

def test_status_emoji_mapping():
    assert get_status_emoji("implemented") == "✅"
    assert get_status_emoji("partial") == "🟡"
    assert get_status_emoji("not_implemented") == "🛑"
    assert get_status_emoji("na") == "⚪"
    assert get_status_emoji("unknown") == "❓"

def test_progress_bar_generation():
    bar = get_progress_bar(50.0, width=10)
    assert "█████░░░░░" in bar
    assert "50.0%" in bar

    bar_full = get_progress_bar(100.0, width=10)
    assert "██████████" in bar_full
    assert "100.0%" in bar_full

def test_confidence_stars():
    assert get_confidence_stars(1.0) == "⭐⭐⭐⭐⭐"
    assert get_confidence_stars(0.5) == "⭐⭐⭐"  # 0.5 * 5 = 2.5 -> 3
    assert get_confidence_stars(0.2) == "⭐"    # 0.2 * 5 = 1.0 -> 1
    assert get_confidence_stars(0.0) == "None"

@pytest.mark.asyncio
async def test_ssp_report_visuals():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/reports/ssp")

    assert response.status_code == 200
    content = response.text

    # Check for progress bar
    assert "Overall Readiness:" in content
    assert "░" in content or "█" in content

    # Check for status emojis in the table
    assert "✅" in content or "🟡" in content or "🛑" in content or "⚪" in content

    # Check for confidence stars (if there are findings)
    # The default mock/empty DB might not have findings, but we can check if the
    # structure is there.
    assert "Confidence:" in content
