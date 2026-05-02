import pytest
import logging
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from backend.main import app
from agents.mistral_agent.agent import agent

@pytest.mark.anyio
async def test_mistral_error_leakage_masked():
    """
    Test that the Mistral agent router NO LONGER leaks internal error details.
    """
    # Mock analyze_gap to raise a sensitive exception
    with patch.object(agent, "analyze_gap", side_effect=Exception("Database connection failed at 192.168.1.5:5432")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Limit system access",
                "control_description": "Limit information system access...",
                "zt_pillar": "User"
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    # Generic message now
    assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_unhandled_exception_leakage():
    """
    Test that unhandled exceptions in any route are caught.
    """
    from agents.orchestrator.agent import _orchestrator

    with patch.object(_orchestrator, "generate_report", side_effect=RuntimeError("Secret internal bug")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/orchestrator/report")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Ensure that normal 404/422 etc are NOT masked by our global handler as generic 500.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/non-existent-route")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"
