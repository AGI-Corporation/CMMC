from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_gap_analysis_error_leakage():
    """
    Verify that the /gap-analysis endpoint does not leak internal error details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.analyze_gap",
        side_effect=Exception(
            "Database connection failed: user=secret_admin password=very_secret"
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {
                "control_id": "AC.1.001",
                "control_title": "Limit access",
                "control_description": "Desc",
                "zt_pillar": "User",
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=req)

        assert response.status_code == 500
        data = response.json()
        # The current implementation returns str(e)
        # We want it to be a generic message
        assert "secret_admin" not in data["detail"]
        assert "very_secret" not in data["detail"]


@pytest.mark.anyio
async def test_code_review_error_leakage():
    """
    Verify that the /code-review endpoint does not leak internal error details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.analyze_code_security",
        side_effect=Exception("Unexpected token at line 42: API_KEY=sk_test_12345"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {"code_snippet": "print('hello')", "language": "python"}
            response = await ac.post("/api/agents/mistral/code-review", json=req)

        assert response.status_code == 500
        data = response.json()
        assert "sk_test_12345" not in data["detail"]


@pytest.mark.anyio
async def test_ask_question_error_leakage():
    """
    Verify that the /ask endpoint does not leak internal error details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.answer_compliance_question",
        side_effect=Exception(
            "Internal Engine Error: Traceback (most recent call last): ..."
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {"question": "How to comply with AC.1.001?"}
            response = await ac.post("/api/agents/mistral/ask", json=req)

        assert response.status_code == 500
        data = response.json()
        assert "Traceback" not in data["detail"]
