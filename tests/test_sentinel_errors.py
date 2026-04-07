from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_mistral_gap_analysis_error_leakage():
    """
    Verify if /api/agents/mistral/gap-analysis leaks internal exception details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("SENSITIVE_DB_CREDENTIALS_LEAKED")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Test",
                    "control_description": "Test",
                    "zt_pillar": "User",
                },
            )

        assert response.status_code == 500
        # If it leaks, "SENSITIVE_DB_CREDENTIALS_LEAKED" will be in the response
        assert "SENSITIVE_DB_CREDENTIALS_LEAKED" not in response.text
        assert response.json()["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_mistral_code_review_error_leakage():
    """
    Verify if /api/agents/mistral/code-review leaks internal exception details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.analyze_code_security"
    ) as mock_analyze:
        mock_analyze.side_effect = Exception("SECRET_API_KEY_EXPOSED")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={"code_snippet": "print('hello')"},
            )

        assert response.status_code == 500
        assert "SECRET_API_KEY_EXPOSED" not in response.text
        assert response.json()["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_mistral_ask_error_leakage():
    """
    Verify if /api/agents/mistral/ask leaks internal exception details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.answer_compliance_question"
    ) as mock_analyze:
        mock_analyze.side_effect = Exception("INTERNAL_STACK_TRACE_DETAILS")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/ask", json={"question": "What is CMMC?"}
            )

        assert response.status_code == 500
        assert "INTERNAL_STACK_TRACE_DETAILS" not in response.text
        assert response.json()["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_global_exception_handler_leakage():
    """
    Verify the global exception handler caught the test exception.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/error-test")

    assert response.status_code == 500
    assert "SECRET_KEY_123" not in response.text
    assert response.json()["detail"] == "Internal server error"
