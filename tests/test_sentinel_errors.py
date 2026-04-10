from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from agents.mistral_agent.agent import MistralComplianceAgent
from backend.main import app


@pytest.mark.anyio
async def test_global_exception_handler():
    """
    Verify that unhandled exceptions return a generic internal server error.
    """

    # Create a temporary endpoint that raises an exception
    @app.get("/api/error-test")
    async def trigger_error():
        raise ValueError("Sensitive database credential: password123")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/api/error-test")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "password123" not in response.text


@pytest.mark.anyio
async def test_http_exception_passthrough():
    """
    Verify that FastAPI HTTPException passes through the global handler.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/api/non-existent-route")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


@pytest.mark.anyio
async def test_validation_error_passthrough():
    """
    Verify that RequestValidationError passes through the global handler.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        # Send invalid data to evidence endpoint to trigger 422
        response = await ac.post("/api/evidence/", json={"invalid": "data"})

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_mistral_agent_error_handling():
    """
    Verify that Mistral agent endpoints return generic error messages.
    """
    with patch.object(
        MistralComplianceAgent,
        "analyze_gap",
        side_effect=Exception("Connection to LLM failed: API_KEY_12345"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
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
    assert response.json() == {"detail": "Internal server error"}
    assert "API_KEY_12345" not in response.text


@pytest.mark.anyio
async def test_mistral_agent_code_review_error_handling():
    with patch.object(
        MistralComplianceAgent,
        "analyze_code_security",
        side_effect=Exception("File system error at /etc/shadow"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={"code_snippet": "print('hello')", "language": "python"},
            )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "/etc/shadow" not in response.text


@pytest.mark.anyio
async def test_mistral_agent_ask_error_handling():
    with patch.object(
        MistralComplianceAgent,
        "answer_compliance_question",
        side_effect=Exception("Internal stack trace details..."),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/ask", json={"question": "What is CMMC?"}
            )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "stack trace" not in response.text
