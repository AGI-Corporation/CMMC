"""
Shared pytest fixtures for the CMMC test suite.
"""
import pytest
from backend.middleware.rate_limit import reset_all_windows


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Flush per-IP rate-limit buckets before every test to prevent 429 errors."""
    reset_all_windows()
    yield
