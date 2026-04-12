import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_error_leakage_generic_exception():
    """
    Verify that an unhandled Exception does not leak internal details.
    """

    @app.get("/test-error-sentinel")
    async def trigger_error():
        raise ValueError(
            "Sensitive database connection string: postgresql://user:password@localhost:5432/db"
        )

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/test-error-sentinel")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


@pytest.mark.anyio
async def test_http_exception_passthrough():
    """
    Verify that explicit HTTPExceptions are still passed through with their detail.
    """

    @app.get("/test-http-error")
    async def trigger_http_error():
        raise HTTPException(status_code=400, detail="Standard validation error")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/test-http-error")

    assert response.status_code == 400
    assert response.json() == {"detail": "Standard validation error"}


@pytest.mark.anyio
async def test_validation_error_passthrough():
    """
    Verify that RequestValidationError is still handled by FastAPI (returning 422).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        # Invalid payload for evidence creation to trigger validation error
        response = await ac.post("/api/evidence/", json={"invalid": "field"})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_mistral_agent_error_leakage_prevention():
    """
    Verify that Mistral agent endpoints don't leak exception details.
    """
    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap"
    ) as mock_gap:
        mock_gap.side_effect = Exception("Internal database failure with secrets")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Title",
                    "control_description": "Desc",
                    "zt_pillar": "User",
                },
            )

        assert response.status_code == 500
        assert response.json() == {"detail": "An error occurred during gap analysis"}
