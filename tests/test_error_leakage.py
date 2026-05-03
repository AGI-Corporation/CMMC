import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.db.database import init_db
from starlette.exceptions import HTTPException as StarletteHTTPException

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.anyio
async def test_error_masking():
    """
    Verify that unhandled exceptions are masked and return a generic 500 message.
    """
    # We'll mock analyze_gap to raise an exception with sensitive info
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=ValueError("SENSITIVE_DB_CREDENTIALS_EXPOSED")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Test",
                "control_description": "Test",
                "zt_pillar": "User"
            })

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "SENSITIVE_DB_CREDENTIALS_EXPOSED" not in response.text

@pytest.mark.anyio
async def test_http_exception_preservation():
    """
    Verify that explicit Starlette/FastAPI HTTPExceptions are preserved (not masked by global handler).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Requesting a non-existent control should return 404
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.anyio
async def test_validation_error_preservation():
    """
    Verify that Pydantic validation errors (422) are preserved.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Missing required fields
        response = await ac.post("/api/agents/mistral/gap-analysis", json={})

    assert response.status_code == 422
    assert "detail" in response.json()
