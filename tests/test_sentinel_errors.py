import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock

from backend.main import app

@pytest.mark.anyio
async def test_global_exception_handler_generic_error():
    """
    Verify that unhandled exceptions are caught by the global handler
    and return a generic 500 message.
    """
    # Create a temporary route that raises an unhandled exception
    @app.get("/api/error-test-unhandled")
    async def error_test_unhandled():
        raise ValueError("Sensitive database connection details: password=12345")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/api/error-test-unhandled")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    # Ensure sensitive info is NOT in the response
    assert "Sensitive" not in response.text
    assert "password" not in response.text

@pytest.mark.anyio
async def test_http_exception_passthrough():
    """
    Verify that HTTPException (like 404) still passes through with its detail.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/api/non-existent-route-123")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

@pytest.mark.anyio
async def test_validation_error_passthrough():
    """
    Verify that RequestValidationError (422) still passes through.
    """
    # Use an existing endpoint that expects a certain body/param
    # /api/reports/ssp expects system_name as a query param (optional),
    # but let's try something that definitely fails validation if possible.
    # Actually, let's just use the evidence creation with invalid data.
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Posting empty JSON to endpoint expecting required fields
        response = await ac.post("/api/evidence/", json={})

    assert response.status_code == 422
    assert "detail" in response.json()

@pytest.mark.anyio
@patch("agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap")
async def test_mistral_agent_error_leakage(mock_analyze):
    """
    Verify that Mistral agent endpoints don't leak exception details.
    """
    mock_analyze.side_effect = Exception("Mistral service is down: API_KEY_INVALID")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.post("/api/agents/mistral/gap-analysis", json={
            "control_id": "AC.1.001",
            "control_title": "Test",
            "control_description": "Test",
            "zt_pillar": "User"
        })

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "API_KEY_INVALID" not in response.text
