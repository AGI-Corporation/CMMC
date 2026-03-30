import os
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_sentinel.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_sentinel.db"):
        os.remove("./test_sentinel.db")


@pytest.mark.anyio
async def test_mistral_error_leakage_gap_analysis():
    """Verify that gap-analysis endpoint does not leak exception details."""
    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap",
        side_effect=ValueError(
            "CRITICAL DATABASE CREDENTIALS EXPOSED: user=admin pass=12345"
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {
                "control_id": "AC.1.001",
                "control_title": "Test Control",
                "control_description": "Desc",
                "zt_pillar": "User",
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=req)

    assert response.status_code == 500
    assert (
        "An internal server error occurred during gap analysis."
        in response.json()["detail"]
    )
    assert "CRITICAL DATABASE CREDENTIALS EXPOSED" not in response.json()["detail"]


@pytest.mark.anyio
async def test_mistral_error_leakage_code_review():
    """Verify that code-review endpoint does not leak exception details."""
    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.analyze_code_security",
        side_effect=Exception(
            "Stack trace: File '/app/backend/db/database.py', line 42, in get_db"
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {"code_snippet": "print('hello')", "language": "python"}
            response = await ac.post("/api/agents/mistral/code-review", json=req)

    assert response.status_code == 500
    assert (
        "An internal server error occurred during code review."
        in response.json()["detail"]
    )
    assert "Stack trace" not in response.json()["detail"]


@pytest.mark.anyio
async def test_mistral_error_leakage_ask():
    """Verify that ask endpoint does not leak exception details."""
    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.answer_compliance_question",
        side_effect=RuntimeError("Connection failed to internal system 10.0.0.5"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            req = {"question": "What is CMMC?"}
            response = await ac.post("/api/agents/mistral/ask", json=req)

    assert response.status_code == 500
    assert (
        "An internal server error occurred while answering the compliance question."
        in response.json()["detail"]
    )
    assert "10.0.0.5" not in response.json()["detail"]


@pytest.mark.anyio
async def test_confidence_validation():
    """Verify that confidence score range validation works."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Test confidence > 1.0
        req = {
            "implementation_status": "implemented",
            "confidence": 1.5,
            "notes": "Invalid confidence",
        }
        response = await ac.patch("/api/controls/AC.1.001", json=req)
        assert response.status_code == 422  # Validation error

        # Test confidence < 0.0
        req["confidence"] = -0.5
        response = await ac.patch("/api/controls/AC.1.001", json=req)
        assert response.status_code == 422

        # Test valid confidence
        req["confidence"] = 0.8
        response = await ac.patch("/api/controls/AC.1.001", json=req)
        assert response.status_code == 200
        assert response.json()["confidence"] == 0.8
