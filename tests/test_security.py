import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


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
async def test_error_detail_masking(monkeypatch):
    """
    Verify that internal error details are masked by the global exception handler.
    """
    from agents.mistral_agent.agent import agent

    async def mock_analyze_gap(*args, **kwargs):
        # Simulate a sensitive error
        raise ValueError("Sensitive internal error detail")

    monkeypatch.setattr(agent, "analyze_gap", mock_analyze_gap)

    # We must set raise_app_exceptions=False to test the app's exception handling
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
    assert response.json()["detail"] == "Internal Server Error"
    assert "Sensitive" not in response.json()["detail"]


@pytest.mark.anyio
async def test_validation_error_remains_unmasked():
    """
    Verify that 422 errors remain informative for the client.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        # Send invalid data (missing required fields)
        response = await ac.post(
            "/api/agents/mistral/gap-analysis",
            json={"invalid": "data"},
        )

    assert response.status_code == 422
    assert "detail" in response.json()


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
