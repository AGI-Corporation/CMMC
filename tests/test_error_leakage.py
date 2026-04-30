import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

@pytest.mark.anyio
async def test_mistral_agent_error_leakage_fixed():
    """
    Verify that the Mistral agent router NO LONGER leaks sensitive error information.
    It should now return 'Internal server error'.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception("Database connection failed; credentials: admin:password123")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Limit system access",
                "control_description": "Limit system access to authorized users",
                "zt_pillar": "User",
                "current_status": "not_implemented",
                "existing_evidence": []
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "admin:password123" not in response.json()["detail"]

@pytest.mark.anyio
async def test_mistral_code_review_error_leakage_fixed():
    with patch("agents.mistral_agent.agent.agent.analyze_code_security", side_effect=Exception("SecretKey leak in stacktrace: XYZ123")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "code_snippet": "print('hello')",
                "language": "python"
            }
            response = await ac.post("/api/agents/mistral/code-review", json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "XYZ123" not in response.json()["detail"]

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that explicit HTTPExceptions (like 404) are still returned correctly and not masked as 500.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
