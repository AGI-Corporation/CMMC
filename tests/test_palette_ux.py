"""
Tests for Palette UX enhancements in SSP reports.
"""
import pytest
from backend.routers.reports import get_status_emoji, get_confidence_stars, get_progress_bar

def test_get_status_emoji():
    assert get_status_emoji("implemented") == "✅"
    assert get_status_emoji("partial") == "🟡"
    assert get_status_emoji("partially_implemented") == "🟡"
    assert get_status_emoji("planned") == "📝"
    assert get_status_emoji("not_implemented") == "🛑"
    assert get_status_emoji("na") == "⚪"
    assert get_status_emoji("unknown") == "⚪"

def test_get_confidence_stars():
    assert get_confidence_stars(1.0) == "⭐⭐⭐⭐⭐"
    assert get_confidence_stars(0.8) == "⭐⭐⭐⭐"
    assert get_confidence_stars(0.5) == "⭐⭐⭐"
    assert get_confidence_stars(0.2) == "⭐"
    assert get_confidence_stars(0.0) == "🌑"

def test_get_progress_bar():
    bar_50 = get_progress_bar(50.0, length=10)
    assert "█████░░░░░" in bar_50
    assert "50.0%" in bar_50

    bar_100 = get_progress_bar(100.0, length=10)
    assert "██████████" in bar_100
    assert "100.0%" in bar_100

    bar_0 = get_progress_bar(0.0, length=10)
    assert "░░░░░░░░░░" in bar_0
    assert "0.0%" in bar_0
