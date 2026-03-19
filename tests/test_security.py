
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.anyio
async def test_security_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    headers = response.headers

    # Check for common security headers
    assert "X-Frame-Options" in headers
    assert "X-Content-Type-Options" in headers
    assert "Referrer-Policy" in headers
    assert "Content-Security-Policy" in headers
