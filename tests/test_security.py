import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


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
async def test_error_masking_mistral_agent(monkeypatch):
    """
    Verify that internal errors in the Mistral agent are masked and do not leak
    implementation details.
    """
    from agents.mistral_agent.agent import agent as mistral_agent

    async def mock_analyze_gap(*args, **kwargs):
        raise ValueError("Secret database credentials: admin:password123")

    # Patch the agent instance used by the router
    monkeypatch.setattr(mistral_agent, "analyze_gap", mock_analyze_gap)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        req = {
            "control_id": "AC.1.001",
            "control_title": "Limit access",
            "control_description": "Desc",
            "zt_pillar": "User",
        }
        response = await ac.post("/api/agents/mistral/gap-analysis", json=req)

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An unexpected error occurred. Please contact support."
    assert "admin:password123" not in str(data)


@pytest.mark.anyio
async def test_validation_error_pass_through():
    """
    Verify that validation errors (422) are still returned with details.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        # Missing required fields
        req = {"control_id": "AC.1.001"}
        response = await ac.post("/api/agents/mistral/gap-analysis", json=req)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # 422 errors usually have a list of location/message details
    assert isinstance(data["detail"], list)


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
