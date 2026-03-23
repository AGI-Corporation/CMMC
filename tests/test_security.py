
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.anyio
async def test_security_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")

    headers = response.headers
    print(f"\nHeaders: {headers}")

    # Check for common security headers
    assert "X-Frame-Options" in headers
    assert "X-Content-Type-Options" in headers
    assert "Content-Security-Policy" in headers
    assert "Strict-Transport-Security" in headers
