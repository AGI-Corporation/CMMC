import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that the current implementation leaks internal error details.
    """
    # Mocking the agent's analyze_gap method to raise a sensitive exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive database connection string: postgresql://user:pass@localhost:5432/db")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Limit system access to authorized users",
                "control_description": "Limit system access to authorized users, processes acting on behalf of authorized users, or devices (including other systems).",
                "zt_pillar": "User"
            }

            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

        # Fixed behavior: returns 500 but detail is masked
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
        assert "Sensitive database connection string" not in response.json()["detail"]

@pytest.mark.anyio
async def test_error_leakage_masking_starlette_http_exception():
    """
    Verify that Starlette/FastAPI HTTPExceptions (like 404) are NOT masked
    as 500 when we implement the fix. For now, just checking baseline.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/api/non-existent-endpoint")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"
