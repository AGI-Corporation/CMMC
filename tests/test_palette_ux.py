import pytest
from backend.routers.reports import get_status_emoji, get_progress_bar, get_confidence_stars

def test_get_status_emoji():
    assert get_status_emoji("implemented") == "✅"
    assert get_status_emoji("partial") == "🟡"
    assert get_status_emoji("partially_implemented") == "🟡"
    assert get_status_emoji("not_implemented") == "🛑"
    assert get_status_emoji("planned") == "📝"
    assert get_status_emoji("na") == "⚪"
    assert get_status_emoji("unknown_status") == "❓"

def test_get_progress_bar():
    # 50% of 20 chars is 10 chars
    bar_50 = get_progress_bar(50.0, width=20)
    assert "█" * 10 in bar_50
    assert "░" * 10 in bar_50
    assert "50.0%" in bar_50

    # 0%
    bar_0 = get_progress_bar(0.0, width=20)
    assert "█" not in bar_0
    assert "░" * 20 in bar_0
    assert "0.0%" in bar_0

    # 100%
    bar_100 = get_progress_bar(100.0, width=20)
    assert "█" * 20 in bar_100
    assert "░" not in bar_100
    assert "100.0%" in bar_100

def test_get_confidence_stars():
    assert get_confidence_stars(1.0) == "⭐⭐⭐⭐⭐"
    assert get_confidence_stars(0.8) == "⭐⭐⭐⭐"
    assert get_confidence_stars(0.5) == "⭐⭐⭐"
    assert get_confidence_stars(0.2) == "⭐"
    assert get_confidence_stars(0.0) == "⭐" # Minimum 1 star
