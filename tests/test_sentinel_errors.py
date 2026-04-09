import logging
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_mistral_error_leakage_gap_analysis():
    """Verify that /api/agents/mistral/gap-analysis doesn't leak exception details."""
    with patch(
        "agents.mistral_agent.agent.MistralComplianceAgent.analyze_gap"
    ) as mock_analyze:
        mock_analyze.side_effect = Exception(
            "Sensitive DB Connection Error: user=admin, pass=secret123"
        )

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Access Control",
                    "control_description": "Limit information system access",
                    "zt_pillar": "User",
                },
            )

        assert response.status_code == 500
        data = response.json()
        assert "Internal server error" in data["detail"]
        assert "Sensitive DB Connection Error" not in data["detail"]
        assert "secret123" not in data["detail"]


@pytest.mark.anyio
async def test_global_exception_handler_leakage():
    """Verify that unhandled exceptions are caught and return a generic message."""
    # We'll use the root endpoint and mock it to raise an error if possible,
    # or just rely on the fact that any unhandled error should be caught.
    # To test the global handler, we can temporarily add a route or mock an existing one.

    with patch("backend.routers.controls.list_controls") as mock_list:
        mock_list.side_effect = Exception("Unexpected runtime crash in core logic!")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/api/controls/")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Internal server error"
        assert "Unexpected runtime crash" not in data["detail"]
