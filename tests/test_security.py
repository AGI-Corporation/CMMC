import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_security_headers():
    """
    Verify that essential security headers are present in the response.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")

    assert response.status_code == 200

    # Check for X-Frame-Options
    assert response.headers.get("X-Frame-Options") == "DENY"

    # Check for X-Content-Type-Options
    assert response.headers.get("X-Content-Type-Options") == "nosniff"

    # Check for X-XSS-Protection
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    # Check for Referrer-Policy
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    # Check for Content-Security-Policy
    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
