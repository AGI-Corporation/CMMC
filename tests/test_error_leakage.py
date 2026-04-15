import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app
from backend.db.database import Base, engine, init_db

@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield

@pytest.mark.anyio
async def test_error_leakage_mistral_gap_analysis():
    """
    Verify that the Mistral gap-analysis endpoint does not leak exception details.
    """
    # Request data
    payload = {
        "control_id": "AC.1.001",
        "control_title": "Limit system access to authorized users",
        "control_description": "Limit information system access to authorized users...",
        "zt_pillar": "User",
        "current_status": "not_implemented",
        "existing_evidence": []
    }

    # Mock the agent's analyze_gap method to raise a sensitive exception
    with patch("agents.mistral_agent.agent.agent.analyze_gap") as mock_analyze:
        mock_analyze.side_effect = Exception("Sensitive database connection string: postgresql://admin:secret_password@db.internal:5432/cmmc")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    # Currently it leaks, so we expect this to FAIL once we start fixing it if we assert it DOES NOT contain it
    # But for now, let's just assert it exists to confirm we have a working test that detects the leak.
    # Actually, Sentinel's job is to fix it, so the test should assert the SAFE state.

    detail = response.json().get("detail", "")
    print(f"\nResponse detail: {detail}")
    assert "secret_password" not in detail
    assert "Sensitive database connection string" not in detail
    assert detail == "Internal server error"

@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that standard HTTPExceptions (like 404) are still returned correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Non-existent evidence ID
        response = await ac.get("/api/evidence/non-existent-id-123")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence non-existent-id-123 not found"
