import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_errors.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_errors.db"):
        os.remove("./test_errors.db")


@pytest.mark.anyio
async def test_global_exception_handler_masking():
    """
    Verify that unhandled exceptions are masked with a generic "Internal server error"
    and do not leak the original exception message.
    """
    # We mock a method that is called by an endpoint to raise an exception.
    # The 'ask_question' endpoint calls 'agent.answer_compliance_question'.
    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.answer_compliance_question",
        side_effect=Exception("SENSITIVE DATABASE ERROR: user_db_prod connection failed at 10.0.1.5"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/ask",
                json={"question": "What is CMMC?"},
            )

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal server error"
    assert "SENSITIVE DATABASE ERROR" not in str(data)


@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that legitimate Starlette/FastAPI HTTPExceptions (4xx) are still
    returned correctly and not masked by the global 500 handler.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Requesting a non-existent control should return 404
        response = await ac.get("/api/controls/NON_EXISTENT_CONTROL")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.anyio
async def test_validation_error_not_swallowed():
    """
    Verify that Pydantic validation errors (422) are still returned correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Sending invalid JSON to the ask endpoint
        response = await ac.post(
            "/api/agents/mistral/ask",
            json={"wrong_field": "test"},
        )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
