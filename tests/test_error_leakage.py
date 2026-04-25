import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_mistral_error_leakage():
    """
    Verify that Mistral agent router does not leak sensitive error details.
    """
    # Mock the analyze_gap method to raise a sensitive exception
    with patch("agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap") as mock_gap:
        mock_gap.side_effect = Exception("Sensitive database connection string: user:pass@host:5432")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Limit system access",
                "control_description": "Limit system access to authorized users",
                "zt_pillar": "User",
                "current_status": "not_implemented"
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

        assert response.status_code == 500
        # Should NOT contain the sensitive info
        assert "Sensitive database connection string" not in response.text
        # Should contain a generic error message
        assert "Internal server error" in response.text or "detail" in response.json()

@pytest.mark.anyio
async def test_404_not_masked():
    """
    Verify that the global exception handler does not mask 404 errors as 500.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/api/non-existent-endpoint")

    assert response.status_code == 404

@pytest.mark.anyio
async def test_validation_error_not_masked():
    """
    Verify that validation errors (422) are still returned correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Send invalid payload (missing required fields)
        response = await ac.post("/api/agents/mistral/gap-analysis", json={})

    assert response.status_code == 422
