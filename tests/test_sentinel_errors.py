import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from unittest.mock import patch
from fastapi import HTTPException

@pytest.mark.anyio
async def test_mistral_error_leak_prevention():
    """
    Verify that 500 errors in Mistral agent endpoints do not leak internal details.
    """
    # Force an error in the agent
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception("Database connection failed: user=admin, pass=secret123")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Limit system access",
                "control_description": "Limit system access to authorized users",
                "zt_pillar": "User"
            })

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "secret123" not in response.text
    assert "Database connection failed" not in response.text

@pytest.mark.anyio
async def test_mistral_code_review_error_leak_prevention():
    """
    Verify that 500 errors in Code Review endpoint do not leak internal details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_code_security", side_effect=Exception("External API Timeout: key=mistral_sk_12345")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/code-review", json={
                "code_snippet": "print('hello')",
                "language": "python"
            })

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "mistral_sk_12345" not in response.text

@pytest.mark.anyio
async def test_mistral_ask_error_leak_prevention():
    """
    Verify that 500 errors in Ask endpoint do not leak internal details.
    """
    with patch("agents.mistral_agent.agent.agent.answer_compliance_question", side_effect=Exception("Internal Stack Trace: ... at line 42")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/ask", json={
                "question": "What is CMMC?"
            })

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "Stack Trace" not in response.text
