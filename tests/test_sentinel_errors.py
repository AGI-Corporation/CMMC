import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_repro():
    """
    Reproduction test to verify that internal error details are leaked in the response.
    """
    # Mocking the analyze_gap method to raise a sensitive exception
    sensitive_message = "Sensitive DB connection string leaked: secret_pwd"

    # We patch the instance's method because the router uses the pre-instantiated 'agent'
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception(sensitive_message)):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Test Control",
                    "control_description": "Test Description",
                    "zt_pillar": "User"
                }
            )

    assert response.status_code == 500
    # Now, it should NOT leak the sensitive message
    assert sensitive_message not in response.json()["detail"]
    assert response.json()["detail"] == "An unexpected error occurred. Please contact support."
