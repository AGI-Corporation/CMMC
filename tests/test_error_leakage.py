import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that the /api/agents/mistral/gap-analysis endpoint does not leak
    sensitive exception details when an internal error occurs.
    """
    # We want to test the case where an exception is raised.
    # Currently, it leaks str(e). We want it to return a generic message.

    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("SENSITIVE_INTERNAL_ERROR_DETAILS")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Test",
                    "control_description": "Test",
                    "zt_pillar": "User"
                }
            )

        assert response.status_code == 500
        # If it leaks str(e), it will contain SENSITIVE_INTERNAL_ERROR_DETAILS
        assert "SENSITIVE_INTERNAL_ERROR_DETAILS" not in response.text
        # It should return a generic error message
        assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_error_leakage_code_review():
    """
    Verify that the /api/agents/mistral/code-review endpoint does not leak
    sensitive exception details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_code_security") as mock_analyze:
        mock_analyze.side_effect = Exception("SECRET_API_KEY_EXPOSED_IN_STACK_TRACE")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={
                    "code_snippet": "print('hello')",
                    "language": "python"
                }
            )

        assert response.status_code == 500
        assert "SECRET_API_KEY_EXPOSED_IN_STACK_TRACE" not in response.text
        assert response.json()["detail"] == "Internal server error"
