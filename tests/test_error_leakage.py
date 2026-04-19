import pytest
import os
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.db.database import Base, engine, init_db

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_error.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_error.db"):
        os.remove("./test_error.db")

@pytest.mark.anyio
async def test_mistral_gap_analysis_error_leakage():
    """
    Verify if the Mistral gap-analysis endpoint leaks sensitive exception details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        sensitive_msg = "Database connection failed at secret-db.internal:5432"
        mock_analyze.side_effect = Exception(sensitive_msg)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Test",
                    "control_description": "Test",
                    "zt_pillar": "User"
                }
            )

        assert response.status_code == 500
        # Verify it DOES NOT leak the detail
        assert sensitive_msg not in response.text
        assert "Internal Server Error" in response.text

@pytest.mark.anyio
async def test_mistral_code_review_error_leakage():
    """
    Verify if the Mistral code-review endpoint leaks sensitive exception details.
    """
    with patch("agents.mistral_agent.agent.agent.analyze_code_security") as mock_analyze:
        sensitive_msg = "FileNotFoundError: [Errno 2] No such file or directory: '/etc/shadow'"
        mock_analyze.side_effect = Exception(sensitive_msg)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={
                    "code_snippet": "print('hello')",
                    "language": "python"
                }
            )

        assert response.status_code == 500
        assert sensitive_msg not in response.text
        assert "Internal Server Error" in response.text

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Ensure that legitimate 404s are still returned correctly and not caught by a
    global handler as 500s (once we add the global handler).
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL")

    assert response.status_code == 404
    assert "not found" in response.text.lower()
