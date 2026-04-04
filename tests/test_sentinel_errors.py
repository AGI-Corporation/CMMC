import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that the /gap-analysis endpoint NO LONGER leaks exception details.
    """
    sensitive_message = "DATABASE_PASSWORD=supersecret123; Connection failed at 192.168.1.50"

    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception(sensitive_message)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Limit system access",
                    "control_description": "Limit access to authorized users",
                    "zt_pillar": "User"
                }
            )

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert sensitive_message not in response.json()["detail"]

@pytest.mark.anyio
async def test_error_leakage_code_review():
    """
    Verify that the /code-review endpoint NO LONGER leaks exception details.
    """
    sensitive_message = "Stack trace: File '/home/user/app/secret_key_loader.py', line 42, in load_key"

    with patch("agents.mistral_agent.agent.agent.analyze_code_security", side_effect=Exception(sensitive_message)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={
                    "code_snippet": "print('hello')",
                    "language": "python"
                }
            )

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert sensitive_message not in response.json()["detail"]

@pytest.mark.anyio
async def test_error_leakage_ask():
    """
    Verify that the /ask endpoint NO LONGER leaks exception details.
    """
    sensitive_message = "Internal API Error: Request failed for https://internal.agi-corp.net/v1/auth"

    with patch("agents.mistral_agent.agent.agent.answer_compliance_question", side_effect=Exception(sensitive_message)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/ask",
                json={
                    "question": "What is CMMC?"
                }
            )

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert sensitive_message not in response.json()["detail"]
