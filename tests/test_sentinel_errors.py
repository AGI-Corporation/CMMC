from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_mistral_error_leakage_prevention():
    """
    Verify that Mistral agent endpoints do not leak exception details.
    """
    # Mock analyze_gap to raise an exception with sensitive info
    sensitive_error = (
        "Database Connection Failed: user='admin' password='secret_password_123'"
    )

    with patch(
        "agents.mistral_agent.agent.agent.analyze_gap",
        side_effect=Exception(sensitive_error),
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
    assert data["detail"] == "Internal server error"
    assert "secret_password_123" not in str(data)
    assert "admin" not in str(data)


@pytest.mark.anyio
async def test_mistral_code_review_error_leakage_prevention():
    """
    Verify that Mistral code-review endpoint does not leak exception details.
    """
    sensitive_error = "File Not Found: /etc/shadow"

    with patch(
        "agents.mistral_agent.agent.agent.analyze_code_security",
        side_effect=Exception(sensitive_error),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {"code_snippet": "print('hello')", "language": "python"}
            response = await ac.post("/api/agents/mistral/code-review", json=req)

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal server error"
    assert "/etc/shadow" not in str(data)


@pytest.mark.anyio
async def test_mistral_ask_error_leakage_prevention():
    """
    Verify that Mistral ask endpoint does not leak exception details.
    """
    sensitive_error = "Mistral API Key Skew: sk_live_51M..."

    with patch(
        "agents.mistral_agent.agent.agent.answer_compliance_question",
        side_effect=Exception(sensitive_error),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {"question": "What is CMMC?"}
            response = await ac.post("/api/agents/mistral/ask", json=req)

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal server error"
    assert "sk_live_51M" not in str(data)
