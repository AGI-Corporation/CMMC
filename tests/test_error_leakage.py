import pytest
import unittest.mock as mock
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.db.database import init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.anyio
async def test_mistral_error_leakage_prevented():
    """
    Verify that the Mistral agent no longer leaks error details.
    """
    with mock.patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception("Sensitive DB Connection String")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Test Control",
                "control_description": "Test Description",
                "zt_pillar": "User"
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

            assert response.status_code == 500
            assert response.json()["detail"] == "Internal server error"
            assert "Sensitive DB Connection String" not in str(response.content)

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that standard FastAPI/Starlette HTTPExceptions are NOT masked by the global handler.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        # Non-existent endpoint should return 404
        response = await ac.get("/api/non-existent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Not Found"

@pytest.mark.anyio
async def test_validation_error_not_swallowed():
    """
    Verify that Pydantic validation errors are still returned correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        # Missing required field 'control_id'
        payload = {
            "zt_pillar": "User"
        }
        response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)
        assert response.status_code == 422
        assert "detail" in response.json()
