import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
import os

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
async def test_mistral_error_leakage():
    """
    Verify that the mistral agent router does not leak sensitive information
    when an exception occurs.
    """
    # Payload for gap-analysis
    payload = {
        "control_id": "AC.1.001",
        "control_title": "Limit system access",
        "control_description": "Limit system access to authorized users",
        "zt_pillar": "User",
        "current_status": "not_implemented"
    }

    # Mock analyze_gap to raise a sensitive exception
    with patch("agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive DB Connection Error: user=admin password=secret")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

        assert response.status_code == 500
        # BEFORE FIX: This might contain the sensitive string
        # AFTER FIX: This should be generic "Internal server error"
        assert "Sensitive DB Connection Error" not in response.text
        assert "password=secret" not in response.text
        assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that standard FastAPI/Starlette HTTPExceptions (like 404)
    are still handled correctly and NOT masked as 500 by the global handler.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/controls/non-existent-id-12345")

    assert response.status_code == 404
    assert response.json()["detail"] == "Control non-existent-id-12345 not found"
