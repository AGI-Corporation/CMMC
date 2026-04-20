import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.db.database import init_db
from unittest.mock import patch

@pytest.fixture(scope="module")
async def setup_db():
    await init_db()
    yield

@pytest.mark.anyio
async def test_error_leakage_mistral_agent(setup_db):
    """
    Verify that Mistral agent endpoints do not leak internal error details.
    """
    # Mock analyze_gap to raise an exception with sensitive info
    with patch("agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap", side_effect=Exception("Database connection failed at 192.168.1.50:5432")):
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Title",
                "control_description": "Desc",
                "zt_pillar": "User"
            })

    assert response.status_code == 500
    # It should NOT leak the error message
    assert "Database connection failed" not in response.json()["detail"]
    assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_http_exception_not_swallowed(setup_db):
    """
    Verify that standard HTTPExceptions (like 404) are still returned correctly.
    """
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        # Request a non-existent control
        response = await ac.get("/api/controls/NON.EXISTENT.123")

    assert response.status_code == 404
    assert response.json()["detail"] == "Control NON.EXISTENT.123 not found"

@pytest.mark.anyio
async def test_validation_error_not_swallowed(setup_db):
    """
    Verify that Pydantic validation errors (422) are still returned correctly.
    """
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        # Send invalid data (missing required fields)
        response = await ac.post("/api/agents/mistral/gap-analysis", json={
            "control_id": "AC.1.001"
        })

    assert response.status_code == 422
    assert "detail" in response.json()
