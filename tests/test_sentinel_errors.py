from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_gap_analysis_error_leakage_prevention():
    """
    Verify that the gap-analysis endpoint DOES NOT leak internal error details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception(
            "Sensitive internal database error with credentials: user=admin pass=12345"
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Limit system access",
                    "control_description": "Limit system access to authorized users",
                    "zt_pillar": "User",
                },
            )

        assert response.status_code == 500
        # Should NOT contain sensitive details
        assert "Sensitive internal database error" not in response.json()["detail"]
        assert "Internal server error during gap analysis" in response.json()["detail"]


@pytest.mark.anyio
async def test_code_review_error_leakage_prevention():
    """
    Verify that the code-review endpoint DOES NOT leak internal error details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.analyze_code_security"
    ) as mock_analyze:
        mock_analyze.side_effect = Exception(
            "Traceback (most recent call last): ... path/to/sensitive/file"
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={"code_snippet": "print('hello')", "language": "python"},
            )

        assert response.status_code == 500
        assert "Traceback" not in response.json()["detail"]
        assert "Internal server error during code review" in response.json()["detail"]


@pytest.mark.anyio
async def test_ask_error_leakage_prevention():
    """
    Verify that the ask endpoint DOES NOT leak internal error details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.answer_compliance_question"
    ) as mock_analyze:
        mock_analyze.side_effect = Exception("API Key 'sk-xxxx' is invalid")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/ask", json={"question": "What is CMMC?"}
            )

        assert response.status_code == 500
        assert "sk-xxxx" not in response.json()["detail"]
        assert (
            "Internal server error during compliance Q&A" in response.json()["detail"]
        )
