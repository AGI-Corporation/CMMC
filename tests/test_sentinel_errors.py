import pytest
import logging
from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException
from backend.main import app

@pytest.mark.anyio
async def test_unhandled_exception_leak_prevention():
    """
    Verify that unhandled exceptions do not leak sensitive information.
    We add a temporary route to the app for this test.
    """
    @app.get("/api/sentinel-error-test")
    async def trigger_error():
        raise ValueError("Secret database credentials leaked: password123")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/api/sentinel-error-test")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal server error"
    assert "password123" not in str(data)
    assert "ValueError" not in str(data)

@pytest.mark.anyio
async def test_http_exception_passthrough():
    """
    Verify that explicit HTTPExceptions (like 404) are still passed through correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Use a path that definitely doesn't exist to trigger a Starlette 404
        response = await ac.get("/api/definitely-does-not-exist-at-all-12345")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

@pytest.mark.anyio
async def test_validation_error_passthrough():
    """
    Verify that RequestValidationError (422) is still passed through correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Invalid payload (missing required fields) for an existing endpoint
        response = await ac.post("/api/evidence/", json={"title": "Missing fields"})

    assert response.status_code == 422
