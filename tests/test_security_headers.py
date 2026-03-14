
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_security_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    # These should fail initially
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "Content-Security-Policy" in response.headers
    assert "Referrer-Policy" in response.headers
