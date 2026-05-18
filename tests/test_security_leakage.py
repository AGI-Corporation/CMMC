import pytest
import os
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.db.database import Base, engine, init_db
from unittest.mock import patch

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
async def test_mistral_error_masked():
    """
    Verify that the Mistral agent no longer leaks internal error details.
    """
    # We need to mock the agent's method to raise an exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Secret database error or API key: sk-123456789")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Limit system access",
                    "control_description": "Limit system access to authorized users",
                    "zt_pillar": "User",
                    "current_status": "not_implemented",
                    "existing_evidence": []
                }
            )

    assert response.status_code == 500
    assert response.json()["detail"] == "An unexpected error occurred. Please contact support."
    assert "sk-123456789" not in response.text

@pytest.mark.anyio
async def test_unhandled_exception_masked():
    """
    Verify how unhandled exceptions are reported and masked.
    """
    with patch("backend.routers.reports.get_latest_assessments") as mock_get:
        mock_get.side_effect = Exception("Internal DB Failure")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            response = await ac.get("/api/reports/ssp")

    assert response.status_code == 500
    assert response.json()["detail"] == "An unexpected error occurred. Please contact support."

@pytest.mark.anyio
async def test_not_found_not_masked():
    """
    Verify that 404 errors still return their specific messages.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Request with a validly formatted but non-existent ID
        response = await ac.get("/api/controls/AC.1.999")

    assert response.status_code == 404
    assert "Control AC.1.999 not found" in response.json()["detail"]
