import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app

from fastapi import HTTPException
from starlette.responses import JSONResponse
from backend.db.database import init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.anyio
async def test_mistral_error_leakage():
    """
    Verify that mistral agent endpoints do not leak internal error details.
    """
    # Mock analyze_gap to raise an exception with sensitive info
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception("Sensitive DB Error: connection failed at 10.0.0.5")):
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
    assert "Sensitive DB Error" not in response.json().get("detail", "")
    assert response.json().get("detail") == "Internal server error"


@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that standard HTTPExceptions are NOT converted to generic 500s.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        # Non-existent control should return 404 via standard HTTPException
        response = await ac.get("/api/controls/NON.EXISTENT.123")

    assert response.status_code == 404
    assert response.json().get("detail") == "Control NON.EXISTENT.123 not found"


@pytest.mark.anyio
async def test_unhandled_exception_mocked():
    """
    Verify that an unhandled exception in a mocked route is caught by global handler.
    """
    # Use a mock to trigger an exception in a legitimate endpoint
    with patch("backend.main.root", side_effect=Exception("Unexpected crash")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.get("/")

    assert response.status_code == 500
    assert response.json().get("detail") == "Internal server error"
