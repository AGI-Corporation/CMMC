from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_gap_analysis_error_leakage():
    """Reproduce error leakage in gap-analysis endpoint."""
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception(
            "Sensitive database error: connection failed at 10.0.0.5"
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Title",
                    "control_description": "Desc",
                    "zt_pillar": "User",
                },
            )

        assert response.status_code == 500
        # SHOULD NOT return the exception message in the detail
        assert "Sensitive database error" not in response.json()["detail"]
        assert "Internal server error" in response.json()["detail"]


@pytest.mark.anyio
async def test_code_review_error_leakage():
    """Reproduce error leakage in code-review endpoint."""
    with patch(
        "agents.mistral_agent.agent.agent.analyze_code_security"
    ) as mock_analyze:
        mock_analyze.side_effect = Exception("File not found at /etc/passwd")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={"code_snippet": "print('hello')", "language": "python"},
            )

        assert response.status_code == 500
        assert "/etc/passwd" not in response.json()["detail"]
        assert "Internal server error" in response.json()["detail"]


@pytest.mark.anyio
async def test_ask_error_leakage():
    """Reproduce error leakage in ask endpoint."""
    with patch(
        "agents.mistral_agent.agent.agent.answer_compliance_question"
    ) as mock_analyze:
        mock_analyze.side_effect = Exception("API Key sk-123456789 expired")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/ask", json={"question": "What is CMMC?"}
            )

        assert response.status_code == 500
        assert "sk-123456789" not in response.json()["detail"]
        assert "Internal server error" in response.json()["detail"]


@pytest.mark.anyio
async def test_global_exception_handler():
    """Verify that unhandled exceptions are caught and return a generic response."""
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/error-test")

    assert response.status_code == 500
    assert "Test exception" not in response.json()["detail"]
    assert "Internal server error" in response.json()["detail"]
