import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from backend.db.database import init_db
from backend.main import app


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    await init_db()


@pytest.mark.anyio
async def test_error_leakage_mistral_gap_analysis():
    """
    Verify that the Mistral gap-analysis endpoint doesn't leak internal error details.
    """
    # Mock analyze_gap to raise an exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception("Sensitive database error details")):
        # We need to set raise_app_exceptions=False so that the global exception handler
        # is invoked and we can check the response it generates.
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Title",
                "control_description": "Description",
                "zt_pillar": "User"
            })

    assert response.status_code == 500
    # If it's leaking, the detail will contain the sensitive message
    assert "Sensitive database error details" not in response.text
    # It should return a generic message
    assert response.json()["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that standard FastAPI/Starlette HTTPExceptions (like 404) are still returned correctly.
    """
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        # Requesting a control that doesn't exist
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL")

    assert response.status_code == 404
    assert response.json()["detail"] == "Control NON_EXISTENT_CONTROL not found"


@pytest.mark.anyio
async def test_validation_exception_preserved():
    """
    Verify that 422 Unprocessable Entity (validation errors) are still returned correctly.
    """
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        # Send invalid JSON (missing required fields)
        response = await ac.post("/api/agents/mistral/gap-analysis", json={
            "control_id": "AC.1.001"
        })

    assert response.status_code == 422
