import os
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app
from backend.db.database import Base, engine, init_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_leakage.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_leakage.db"):
        os.remove("./test_leakage.db")


@pytest.mark.anyio
async def test_error_leakage_mistral():
    """
    Test that the Mistral agent doesn't leak sensitive error details in its response.
    Verified that it now returns "Internal server error" instead of exception details.
    """
    # Mocking the analyze_gap method to raise a sensitive exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive info: DB_PASSWORD=secret123")

        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Title",
                "control_description": "Desc",
                "zt_pillar": "User"
            })

        assert response.status_code == 500
        assert "secret123" not in response.text
        assert response.json()["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Test that explicit HTTPExceptions (like 404) are NOT swallowed by the global handler
    and still return their intended status and detail.
    """
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        # Use a non-existent control ID to trigger 404
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL_ID")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_validation_error_preserved():
    """
    Test that request validation errors (422) are still returned correctly.
    """
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        # Missing required fields in POST body to trigger 422
        response = await ac.post("/api/agents/mistral/gap-analysis", json={})

    assert response.status_code == 422
    assert "detail" in response.json()
