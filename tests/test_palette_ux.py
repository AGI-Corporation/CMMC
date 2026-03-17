import pytest
from backend.routers.reports import get_status_emoji, get_progress_bar, get_confidence_stars

def test_get_status_emoji():
    assert get_status_emoji("implemented") == "✅"
    assert get_status_emoji("partial") == "🟡"
    assert get_status_emoji("partially_implemented") == "🟡"
    assert get_status_emoji("planned") == "📝"
    assert get_status_emoji("not_implemented") == "🛑"
    assert get_status_emoji("na") == "⚪"
    assert get_status_emoji("unknown") == "⚪"

def test_get_progress_bar():
    bar = get_progress_bar(50, width=10)
    assert "█████░░░░░" in bar
    assert "50.0%" in bar

    bar_full = get_progress_bar(100, width=10)
    assert "██████████" in bar_full
    assert "100.0%" in bar_full

def test_get_confidence_stars():
    assert get_confidence_stars(1.0) == "⭐⭐⭐⭐⭐"
    assert get_confidence_stars(0.8) == "⭐⭐⭐⭐"
    assert get_confidence_stars(0.5) == "⭐⭐⭐"  # 0.5 * 5 = 2.5 -> 3
    assert get_confidence_stars(0.4) == "⭐⭐"   # 0.4 * 5 = 2.0 -> 2
    assert get_confidence_stars(0.2) == "⭐"    # 0.2 * 5 = 1.0 -> 1
    assert get_confidence_stars(0.0) == "⭐"    # min 1 star
