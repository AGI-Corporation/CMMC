import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_security_headers():
    """Verify that security headers are present in responses."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none';"

@pytest.mark.asyncio
async def test_security_headers_health():
    """Verify that security headers are present in health check responses."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none';"
