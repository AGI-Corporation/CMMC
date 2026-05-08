import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app
from backend.models.evidence import EvidenceCreate


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_security.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_security.db"):
        os.remove("./test_security.db")


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
async def test_error_masking():
    """
    Verify that unhandled exceptions are masked by the global exception handler.
    """

    # We need to trigger an exception that isn't a StarletteHTTPException
    # Let's mock a router to raise a generic Exception
    @app.get("/trigger-error")
    async def trigger_error():
        raise ValueError("Sensitive internal error message")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/trigger-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


@pytest.mark.anyio
async def test_uri_validation():
    """
    Verify that invalid URIs are rejected by the Evidence model.
    """
    invalid_data = {
        "control_id": "AC.1.001",
        "zt_pillar": "User",
        "evidence_type": "log",
        "title": "Invalid URI Test",
        "description": "Testing SSRF protection",
        "source_system": "Test System",
        "uri": "not-a-url",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/evidence/", json=invalid_data)

    assert response.status_code == 422
    # Verify it's a validation error for the URI field
    details = response.json()["detail"]
    assert any(d["loc"] == ["body", "uri"] for d in details)


@pytest.mark.anyio
async def test_valid_uri_accepted():
    """
    Verify that valid URIs are still accepted.
    """
    valid_data = {
        "control_id": "AC.1.001",
        "zt_pillar": "User",
        "evidence_type": "log",
        "title": "Valid URI Test",
        "description": "Testing valid URI",
        "source_system": "Test System",
        "uri": "https://example.com/evidence.log",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/evidence/", json=valid_data)

    assert response.status_code == 200
    assert response.json()["uri"] == "https://example.com/evidence.log"


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
