import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app
from backend.db.database import Base, engine, init_db
import os

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_leakage.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_leakage.db"):
        os.remove("./test_leakage.db")

@pytest.mark.anyio
async def test_error_leakage_gap_analysis():
    """
    Verify that the /gap-analysis endpoint currently leaks exception details.
    """
    # Use raise_app_exceptions=False to let the exception handler (if any) or
    # FastAPI's default handle the error so we can check the response.
    # Currently there is no custom handler, so it might bubble up or
    # be caught by FastAPI's default.
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
            mock_analyze.side_effect = Exception("Sensitive database connection error: user=admin pass=secret")

            payload = {
                "control_id": "AC.1.001",
                "control_title": "Limit system access to authorized users",
                "control_description": "...",
                "zt_pillar": "User",
                "current_status": "not_implemented",
                "existing_evidence": []
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

            assert response.status_code == 500
            # It should NOT leak the sensitive error
            assert "Sensitive database connection error" not in response.json()["detail"]
            assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_error_leakage_code_review():
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        with patch("agents.mistral_agent.agent.agent.analyze_code_security") as mock_review:
            mock_review.side_effect = Exception("Internal file path leaked: /etc/passwd")

            payload = {
                "code_snippet": "print('hello')",
                "language": "python"
            }
            response = await ac.post("/api/agents/mistral/code-review", json=payload)

            assert response.status_code == 500
            assert "/etc/passwd" not in response.json()["detail"]
            assert response.json()["detail"] == "Internal server error"

@pytest.mark.anyio
async def test_error_not_leaked_http_exception():
    """
    Verify that built-in FastAPI exceptions (like 404) are NOT swallowed
    by the global handler and are returned correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL")
        assert response.status_code == 404
        assert "NON_EXISTENT_CONTROL not found" in response.json()["detail"]
