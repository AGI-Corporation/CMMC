import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException
from backend.main import app
from unittest.mock import patch

@pytest.mark.anyio
async def test_global_exception_handler_leakage():
    """
    Test that unhandled exceptions do not leak sensitive information.
    """
    # We'll mock a helper function called by the endpoint to raise an unexpected exception
    with patch("backend.routers.reports.get_latest_assessments", side_effect=ValueError("Secret database connection string leaked!")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/reports/ssp")

    assert response.status_code == 500
    assert "Secret database connection string leaked!" not in response.text
    assert response.json() == {"detail": "Internal server error"}

@pytest.mark.anyio
async def test_mistral_agent_error_leakage():
    """
    Test that Mistral agent does not leak exception details in 500 responses.
    """
    # Mocking analyze_gap to raise an exception
    with patch("agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap", side_effect=RuntimeError("Sensitive API Error details")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Test",
                "control_description": "Test",
                "zt_pillar": "User"
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    assert "Sensitive API Error details" not in response.text
    assert response.json() == {"detail": "Internal server error"}
