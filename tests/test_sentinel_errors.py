import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_mistral_error_leakage():
    """
    Verify that Mistral agent endpoints do not leak exception details in 500 responses.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Mocking analyze_gap to raise an exception
        with patch("agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap", side_effect=Exception("Sensitive DB credential leaked!")):
            req = {
                "control_id": "AC.1.001",
                "control_title": "Limit access",
                "control_description": "Desc",
                "zt_pillar": "User",
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=req)

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
            assert "Sensitive DB credential" not in response.json()["detail"]

@pytest.mark.anyio
async def test_confidence_range_validation():
    """
    Verify that confidence scores outside 0.0-1.0 range are rejected.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Test updating a control with invalid confidence
        update_req = {
            "implementation_status": "implemented",
            "confidence": 1.5,
            "notes": "Invalid confidence"
        }
        response = await ac.patch("/api/controls/AC.1.001", json=update_req)
        assert response.status_code == 422 # Unprocessable Entity

        update_req["confidence"] = -0.5
        response = await ac.patch("/api/controls/AC.1.001", json=update_req)
        assert response.status_code == 422
