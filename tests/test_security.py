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

from unittest.mock import patch

@pytest.mark.anyio
async def test_error_masking_information_disclosure():
    """
    Verify that sensitive internal error details are leaked in the current implementation.
    This test is expected to pass (showing the vulnerability) before the fix,
    and then we will update it to expect masked errors after the fix.
    """
    from agents.mistral_agent.agent import agent

    sensitive_message = "Sensitive internal error details: DB connection string leaked or similar"

    # We need to configure the client to NOT raise app exceptions so we can check the 500 response
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        with patch.object(agent, "analyze_gap", side_effect=Exception(sensitive_message)):
            payload = {
                "control_id": "AC.1.001",
                "control_title": "Limit system access to authorized users",
                "control_description": "Standard control",
                "zt_pillar": "User",
                "current_status": "not_implemented",
                "existing_evidence": []
            }
            response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)

    assert response.status_code == 500
    # New behavior: masks the sensitive exception message
    assert response.json()["detail"] == "An unexpected error occurred. Please contact support."
    assert sensitive_message not in response.json()["detail"]

@pytest.mark.anyio
async def test_evidence_uri_validation():
    """
    Verify that the uri field in EvidenceCreate is validated as a proper URL.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        # Invalid URI
        payload = {
            "control_id": "AC.1.001",
            "zt_pillar": "User",
            "evidence_type": "log",
            "title": "Invalid URI Test",
            "description": "Testing URL validation",
            "source_system": "Test System",
            "uri": "not-a-url"
        }
        response = await ac.post("/api/evidence/", json=payload)
        assert response.status_code == 422

        # Valid URI
        payload["uri"] = "https://example.com/evidence.log"
        response = await ac.post("/api/evidence/", json=payload)
        assert response.status_code == 200
