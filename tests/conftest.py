"""
Shared pytest fixtures for the CMMC test suite.
"""
import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    """Tell the anyio pytest plugin to use asyncio as the event loop backend."""
    return "asyncio"
