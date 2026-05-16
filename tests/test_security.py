from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.anyio
async def test_error_masking_mistral_gap_analysis():
    """
    Verify that Mistral gap-analysis masks error details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.analyze_gap",
        side_effect=Exception("Mistral API Failure: connection_string=db://root:pass"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/gap-analysis",
                json={
                    "control_id": "AC.1.001",
                    "control_title": "Title",
                    "control_description": "Desc",
                    "zt_pillar": "User",
                },
            )

    assert response.status_code == 500
    content = response.json()["detail"]
    assert "Mistral API Failure" not in content
    assert "connection_string" not in content
    assert "unexpected error occurred" in content.lower()


@pytest.mark.anyio
async def test_error_masking_mistral_code_review():
    """
    Verify that Mistral code-review masks error details.
    """
    with patch(
        "agents.mistral_agent.agent.agent.analyze_code_security",
        side_effect=Exception("Internal Secret API Key: 12345"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/api/agents/mistral/code-review",
                json={"code_snippet": "print('hello')", "language": "python"},
            )

    assert response.status_code == 500
    content = response.json()["detail"]
    assert "Internal Secret API Key: 12345" not in content
    assert "unexpected error occurred" in content.lower()


@pytest.mark.anyio
async def test_error_masking_generic_exception():
    """
    Verify that an unhandled Exception is masked with a generic message.
    """
    # Use patch to trigger an exception in an endpoint
    with patch("backend.routers.reports.get_latest_assessments", side_effect=Exception("Database connection failed: user=admin pass=secret123")):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/reports/ssp")

    assert response.status_code == 500
    content = response.json()["detail"]
    assert "Database connection failed" not in content
    assert "secret123" not in content
    assert "unexpected error occurred" in content.lower()


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
