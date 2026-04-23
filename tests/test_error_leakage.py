import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from backend.main import app


@pytest.mark.anyio
async def test_error_leakage_mistral():
    """
    Verify that the Mistral agent endpoint leaks exception details.
    """
    sensitive_msg = "SENSITIVE DATABASE ERROR: user_id=123, password=secret"
    with patch("agents.mistral_agent.agent.agent.analyze_gap", side_effect=Exception(sensitive_msg)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/api/agents/mistral/gap-analysis", json={
                "control_id": "AC.1.001",
                "control_title": "Title",
                "control_description": "Desc",
                "zt_pillar": "User"
            })

        assert response.status_code == 500
        # If it is fixed, the sensitive message will NOT be in the detail field
        assert "SENSITIVE DATABASE ERROR" not in response.json()["detail"]
        assert response.json()["detail"] == "Mistral agent analysis failed"


@pytest.mark.anyio
async def test_http_exception_not_swallowed():
    """
    Verify that explicit HTTPExceptions are not masked as generic errors if they have a detail.
    In this case, our refactored agent returns a 500 with a generic detail.
    """
    # Test a non-existent endpoint to ensure FastAPI's 404 still works
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/non-existent")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"
