import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app, init_db

@pytest.fixture
async def setup_db():
    await init_db()

@pytest.mark.anyio
async def test_mistral_gap_analysis_error_leakage_fixed(setup_db):
    """
    Verify that the /api/agents/mistral/gap-analysis endpoint no longer leaks internal error details.
    """
    payload = {
        "control_id": "AC.1.001",
        "control_title": "Limit system access",
        "control_description": "Limit access to authorized users.",
        "zt_pillar": "User",
        "current_status": "not_implemented",
        "existing_evidence": []
    }

    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception("Sensitive database error: connection string exposed")):
        # We need raise_app_exceptions=False for httpx to not raise the exception and instead return the response
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    assert "Internal server error" in response.text
    assert "Sensitive database error" not in response.text

@pytest.mark.anyio
async def test_mistral_code_review_error_leakage_fixed(setup_db):
    """
    Verify that the /api/agents/mistral/code-review endpoint no longer leaks internal error details.
    """
    payload = {
        "code_snippet": "print('hello')",
        "language": "python"
    }

    with patch("agents.mistral_agent.agent.agent.analyze_code_security", side_effect=Exception("Unexpected engine failure in Codestral")):
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/code-review", json=payload)

    assert response.status_code == 500
    assert "Internal server error" in response.text
    assert "Unexpected engine failure" not in response.text

@pytest.mark.anyio
async def test_mistral_ask_error_leakage_fixed(setup_db):
    """
    Verify that the /api/agents/mistral/ask endpoint no longer leaks internal error details.
    """
    payload = {
        "question": "What is CMMC?",
        "context": ""
    }

    with patch("agents.mistral_agent.agent.agent.answer_compliance_question", side_effect=Exception("Mistral API Timeout - Key: sk-123456789")):
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/ask", json=payload)

    assert response.status_code == 500
    assert "Internal server error" in response.text
    assert "sk-123456789" not in response.text

@pytest.mark.anyio
async def test_http_exception_not_swallowed(setup_db):
    """
    Verify that standard FastAPI/Starlette HTTPExceptions are still handled correctly (not masked by global handler).
    """
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL")

    assert response.status_code == 404
    assert "Control NON_EXISTENT_CONTROL not found" in response.text
