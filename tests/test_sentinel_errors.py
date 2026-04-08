import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from unittest.mock import patch

@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that the /gap-analysis endpoint does not leak internal error details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive database error: connection failed for user 'admin' with password 'password123'")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Test",
                "control_description": "Test",
                "zt_pillar": "User"
            })

        assert response.status_code == 500
        # The sensitive info should NOT be in the response
        assert "password123" not in response.text
        assert "Internal server error during gap analysis" in response.text

@pytest.mark.anyio
async def test_error_leakage_global_handler():
    """
    Verify that the global exception handler masks unhandled exceptions.
    """
    # Create a temporary endpoint for testing
    @app.get("/api/error-test-temp")
    async def error_test_temp():
        raise Exception("Sensitive info: secret_data_123")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/error-test-temp")

    assert response.status_code == 500
    assert "secret_data_123" not in response.text
    assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_error_leakage_code_review():
    """
    Verify that the /code-review endpoint does not leak internal error details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_code_security") as mock_analyze:
        mock_analyze.side_effect = Exception("Internal file path: /usr/local/secret/app/config.py not found")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/code-review", json={
                "code_snippet": "print('hello')",
                "language": "python"
            })

        assert response.status_code == 500
        assert "/usr/local/secret" not in response.text
        assert "Internal server error" in response.text or "An unexpected error occurred" in response.text
