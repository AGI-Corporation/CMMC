
import pytest
from backend.routers.reports import get_status_emoji, get_confidence_stars, get_progress_bar

def test_get_status_emoji():
    assert get_status_emoji("implemented") == "✅"
    assert get_status_emoji("partial") == "🟡"
    assert get_status_emoji("partially_implemented") == "🟡"
    assert get_status_emoji("planned") == "🟡"
    assert get_status_emoji("not_implemented") == "🛑"
    assert get_status_emoji("not_started") == "⚪"
    assert get_status_emoji("NA") == "⚪"

def test_get_confidence_stars():
    assert get_confidence_stars(1.0) == "⭐⭐⭐⭐⭐"
    assert get_confidence_stars(0.0) == "☆☆☆☆☆"
    assert get_confidence_stars(0.5) == "⭐⭐⭐☆☆"  # 0.5 * 5 + 0.5 = 3
    assert get_confidence_stars(0.4) == "⭐⭐☆☆☆"  # 0.4 * 5 + 0.5 = 2.5 -> 2
    assert get_confidence_stars(0.7) == "⭐⭐⭐⭐☆"  # 0.7 * 5 + 0.5 = 4.0 -> 4

def test_get_progress_bar():
    bar = get_progress_bar(50.0, width=10)
    assert "█████░░░░░" in bar
    assert "50.0%" in bar

    bar_full = get_progress_bar(100.0, width=10)
    assert "██████████" in bar_full
    assert "100.0%" in bar_full
