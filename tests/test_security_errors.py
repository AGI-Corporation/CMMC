import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_error_masking_internal_server_error():
    """
    Verify that sensitive internal error details are masked and replaced with a generic message.
    """
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
    assert sensitive_message not in response.json()["detail"]
    assert response.json()["detail"] == "An unexpected error occurred. Please contact support."

@pytest.mark.anyio
async def test_validation_error_not_masked():
    """
    Verify that 422 validation errors are still returned to the client (not masked to 500).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Missing required fields in the request body
        response = await ac.post(
            "/api/agents/mistral/gap-analysis",
            json={"control_id": "AC.1.001"}
        )

    assert response.status_code == 422
    assert "detail" in response.json()
    # Ensure it's the standard FastAPI validation detail, not our masked message
    assert response.json()["detail"] != "An unexpected error occurred. Please contact support."
