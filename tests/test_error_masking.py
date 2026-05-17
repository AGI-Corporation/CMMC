import pytest
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient
from backend.main import app

@pytest.mark.anyio
async def test_error_masking():
    """
    Verify that internal error details are MASKED
    when an exception occurs in the Mistral agent routes.
    """
    # Mock agent.analyze_gap to raise an exception with sensitive info
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive internal database connection error: DB_PASSWORD=secret")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Limit information system access to authorized users",
                "control_description": "...",
                "zt_pillar": "User"
            })

    assert response.status_code == 500
    # Verify it is MASKED
    detail = response.json()["detail"]
    assert detail == "An unexpected error occurred. Please contact support."
    assert "Sensitive" not in detail
    assert "DB_PASSWORD" not in detail
