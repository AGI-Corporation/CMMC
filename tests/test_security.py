import sys
from unittest.mock import MagicMock

import pytest

# Mock mistralai before importing app
sys.modules["mistralai"] = MagicMock()

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
async def test_error_masking(monkeypatch):
    """
    Verify that internal server errors are masked and do not leak sensitive info.
    """
    from backend.routers.reports import get_latest_assessments

    # Mock a function to raise an unexpected error
    def mock_error(*args, **kwargs):
        raise ValueError("Secret database credentials or stack trace")

    monkeypatch.setattr("backend.routers.reports.get_latest_assessments", mock_error)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        # This endpoint calls get_latest_assessments
        response = await ac.get("/api/reports/ssp")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal server error occurred."
    assert "Secret" not in str(data)
    assert "ValueError" not in str(data)


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
