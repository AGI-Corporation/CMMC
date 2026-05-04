import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that the /gap-analysis endpoint does NOT leak error details.
    """
    # Mock analyze_gap to raise a sensitive exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive database error: connection string exposed sk_live_123")

        # We need to set raise_app_exceptions=False to test the global exception handler
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Access Control",
                "control_description": "Limit information system access",
                "zt_pillar": "User"
            })

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "Internal server error" in detail
    assert "sk_live_123" not in detail
    assert "Sensitive database error" not in detail

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that 404 errors are still returned correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/mistral/non-existent-endpoint")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"
