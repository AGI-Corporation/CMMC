import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_validation_error_not_masked():
    """
    Verify that validation errors still return 422, not 500 (masked by global handler).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        # Missing required fields should trigger RequestValidationError
        response = await ac.post(
            "/api/agents/mistral/gap-analysis",
            json={"control_id": "missing_other_fields"}
        )

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_security_headers():
    """
    Verify that SecurityHeadersMiddleware correctly adds the required headers.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains"
    )
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.anyio
async def test_error_masking_gap_analysis(monkeypatch):
    """
    Verify that internal error details are not leaked in the /api/agents/mistral/gap-analysis endpoint.
    """

    async def mock_analyze_gap(*args, **kwargs):
        raise ValueError(
            "Sensitive internal error: Database connection string 'admin:password123@db.internal' failed"
        )

    # Patch the agent instance method used in the router
    from agents.mistral_agent.agent import agent as mistral_agent

    monkeypatch.setattr(mistral_agent, "analyze_gap", mock_analyze_gap)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.post(
            "/api/agents/mistral/gap-analysis",
            json={
                "control_id": "AC.1.001",
                "control_title": "Limit information system access",
                "control_description": "Limit information system access to authorized users",
                "zt_pillar": "User",
                "current_status": "not_implemented",
                "existing_evidence": [],
            },
        )

    assert response.status_code == 500
    # Before fix, this will contain the sensitive string
    # After fix, it should be a generic message
    detail = response.json().get("detail", "")
    assert "Sensitive internal error" not in detail
    assert detail == "An unexpected error occurred. Please contact support."


@pytest.mark.anyio
async def test_security_headers_root():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains"
    )
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
