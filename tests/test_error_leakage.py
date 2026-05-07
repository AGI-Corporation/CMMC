
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_masked():
    """
    Verify that unhandled exceptions return a generic error message.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive internal database error details")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Limit system access",
                "control_description": "Limit system access to authorized users",
                "zt_pillar": "User"
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    assert "Internal server error" in response.text
    assert "Sensitive internal database error details" not in response.text

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that StarletteHTTPExceptions (like 404) still return their intended detail.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/api/nonexistent-endpoint")

    assert response.status_code == 404
    assert "Not Found" in response.text

@pytest.mark.anyio
async def test_validation_error_preserved():
    """
    Verify that 422 validation errors are still returned with detail.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Send invalid payload to a POST endpoint
        response = await ac.post("/api/agents/mistral/gap-analysis", json={"invalid": "field"})

    assert response.status_code == 422
    assert "detail" in response.json()
