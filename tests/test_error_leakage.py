import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app
from backend.db.database import init_db

@pytest.fixture
async def setup_db():
    await init_db()
    yield

@pytest.mark.anyio
async def test_global_exception_handler_masking(setup_db):
    """
    Verify that unhandled exceptions are masked with a generic message.
    """
    # Mocking analyze_gap to raise an unexpected exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception("Database connection failed! secret_token=12345")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Access Control",
                "control_description": "Limit information system access",
                "zt_pillar": "User",
                "current_status": "not_implemented",
                "existing_evidence": []
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "secret_token" not in response.text

@pytest.mark.anyio
async def test_http_exception_not_swallowed(setup_db):
    """
    Verify that StarletteHTTPException (like 404) still returns its detail.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Non-existent endpoint
        response = await ac.get("/api/non-existent")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

@pytest.mark.anyio
async def test_validation_error_preserved(setup_db):
    """
    Verify that 422 Unprocessable Entity (validation errors) are still returned.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Missing required fields in payload
        payload = {"control_id": "AC.1.001"}
        response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()
