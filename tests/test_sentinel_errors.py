import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_error_leakage():
    # Adding a temporary route to trigger an error
    @app.get("/api/test-error-leakage")
    async def trigger_error():
        raise ValueError("Sensitive database connection string: postgresql://user:password@localhost:5432/db")

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        response = await ac.get("/api/test-error-leakage")

    assert response.status_code == 500
    assert "Sensitive database connection string" not in response.text
    assert "password" not in response.text
    assert "Internal server error" in response.text

@pytest.mark.asyncio
async def test_http_exception_passthrough():
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        response = await ac.get("/api/controls/NONEXISTENT")

    assert response.status_code == 404
    assert "Control NONEXISTENT not found" in response.text

@pytest.mark.asyncio
async def test_validation_error_passthrough():
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        # Sending invalid data to a POST endpoint
        response = await ac.post("/api/agents/mistral/gap-analysis", json={"invalid": "data"})

    assert response.status_code == 422
    assert "detail" in response.json()
