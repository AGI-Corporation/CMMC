import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_demonstration():
    """
    Demonstrates that internal errors currently leak sensitive details.
    This test is expected to fail (or rather, confirm the leak) before the fix.
    """
    sensitive_message = "Sensitive internal database error: connection string=postgres://user:pass@secret.db"

    # Mocking the agent to raise an exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception(sensitive_message)

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Access Control",
                "control_description": "Limit information system access to authorized users.",
                "zt_pillar": "User"
            })

        assert response.status_code == 500
        detail = response.json().get("detail")
        print(f"DEBUG: Error detail received: {detail}")

        # Verify the leak is now GONE
        assert sensitive_message not in str(detail)
        assert detail == "Internal server error"
