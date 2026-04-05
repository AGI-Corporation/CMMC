from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that sensitive error details are not leaked in the /api/agents/mistral/gap-analysis response.
    """
    sensitive_msg = "CRITICAL: Database connection failed for user: admin_superuser. Secret: sk_live_12345"

    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap",
        side_effect=Exception(sensitive_msg),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Limit system access",
                    "control_description": "Limit information system access...",
                    "zt_pillar": "User",
                },
            )

    assert response.status_code == 500
    # Verify that sensitive info is NOT leaked in the response
    assert sensitive_msg not in response.text
    assert "An internal error occurred" in response.text


@pytest.mark.anyio
async def test_error_leakage_code_review():
    """
    Verify that sensitive error details are not leaked in the /api/agents/mistral/code-review response.
    """
    sensitive_msg = "Internal stack trace: File '/app/backend/db/database.py', line 42, in get_db. Permission denied for /etc/shadow"

    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.analyze_code_security",
        side_effect=Exception(sensitive_msg),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={"code_snippet": "print('hello')", "language": "python"},
            )

    assert response.status_code == 500
    assert sensitive_msg not in response.text
    assert "An internal error occurred" in response.text


@pytest.mark.anyio
async def test_error_leakage_ask():
    """
    Verify that sensitive error details are not leaked in the /api/agents/mistral/ask response.
    """
    sensitive_msg = "Error 504: Gateway Timeout to internal IP 10.0.0.5"

    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.answer_compliance_question",
        side_effect=Exception(sensitive_msg),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/ask", json={"question": "What is CMMC?"}
            )

    assert response.status_code == 500
    assert sensitive_msg not in response.text
    assert "An internal error occurred" in response.text
