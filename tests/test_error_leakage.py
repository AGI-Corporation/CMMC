import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from backend.main import app

@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that an exception in the agent router is caught and redacted.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive database connection string leaked!")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Test",
                "control_description": "Test",
                "zt_pillar": "User"
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

        assert response.status_code == 500
        # Verified: sensitive message is NO LONGER leaked
        assert response.json()["detail"] == "Error during gap analysis"
        assert "Sensitive database connection string leaked!" not in response.json()["detail"]

@pytest.mark.anyio
async def test_error_leakage_code_review():
    with patch("agents.mistral_agent.agent.agent.analyze_code_security") as mock_analyze:
        mock_analyze.side_effect = Exception("Secret key leakage in traceback!")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "code_snippet": "print('hello')",
                "language": "python"
            }
            response = await ac.post("/api/agents/mistral/code-review", json=payload)

        assert response.status_code == 500
        # Verified: sensitive message is NO LONGER leaked
        assert response.json()["detail"] == "Error during code review"
        assert "Secret key leakage in traceback!" not in response.json()["detail"]

@pytest.mark.anyio
async def test_unhandled_exception_leakage():
    """
    Verify that a completely unhandled exception (not caught by router)
    is caught by the global handler and redacted.
    """
    with patch("backend.routers.evidence.EvidenceRecord", side_effect=RuntimeError("Raw DB Error!")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "zt_pillar": "User",
                "evidence_type": "log",
                "title": "Test",
                "description": "Test",
                "source_system": "Test"
            }
            response = await ac.post("/api/evidence/", json=payload)

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
        assert "Raw DB Error!" not in response.json()["detail"]

@pytest.mark.anyio
async def test_global_handler_preserves_404():
    """
    Ensure that the global exception handler doesn't mask 404 errors as 500s.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/non-existent-route")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"

@pytest.mark.anyio
async def test_global_handler_preserves_422():
    """
    Ensure that validation errors (422) are still returned correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Send invalid payload to evidence endpoint
        response = await ac.post("/api/evidence/", json={"invalid": "payload"})

    assert response.status_code == 422
