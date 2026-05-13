import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_mistral_gap_analysis():
    """
    Verify that the Mistral gap-analysis endpoint does not leak internal error details.
    """
    # Mock analyze_gap to raise an exception with sensitive info
    with patch("agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap", side_effect=Exception("Sensitive database error: connection string 'postgres://user:pass@localhost'")):
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
    # Verify masking
    data = response.json()
    assert "Sensitive database error" not in data["detail"]
    assert data["detail"] == "Internal Server Error"

@pytest.mark.anyio
async def test_validation_error_leakage():
    """
    Verify that 422 errors still return details (as they are usually safe).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        # Send invalid payload (missing control_id)
        response = await ac.post("/api/agents/mistral/gap-analysis", json={
            "control_title": "Test"
        })

    assert response.status_code == 422
    assert "detail" in response.json()
    assert isinstance(response.json()["detail"], list) # FastAPI default 422 format
