"""
Shared pytest fixtures for the CMMC Compliance Platform test suite.
"""

import pytest

from backend.middleware.rate_limit import reset_all_windows


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Reset all rate-limit sliding windows before each test.

    Without this fixture, cumulative request counts across tests in a session
    can exceed the configured limit and cause unexpected HTTP 429 responses.
    """
    reset_all_windows()
    yield
