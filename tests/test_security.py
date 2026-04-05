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


# ─── MCP Auth Middleware Tests ─────────────────────────────────────────────────

JSONRPC_UNAUTH = {
    "jsonrpc": "2.0",
    "error": {"code": -32001, "message": "Unauthorized \u2014 Bearer token required"},
    "id": None,
}


@pytest.mark.anyio
async def test_mcp_auth_no_key_env_allows_through(monkeypatch):
    """When MCP_API_KEY is not set, the middleware allows requests (dev mode)."""
    import backend.middleware.mcp_auth as mcp_auth
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    monkeypatch.setattr(mcp_auth, "_MCP_API_KEY", "")

    # Use a minimal app so we don't hang on the real MCP SSE endpoint.
    async def mcp_stub(request):
        return JSONResponse({"ok": True})

    stub = Starlette(routes=[Route("/mcp", mcp_stub, methods=["GET", "POST"])])
    stub.add_middleware(mcp_auth.MCPAuthMiddleware)

    async with AsyncClient(
        transport=ASGITransport(app=stub), base_url="http://test"
    ) as ac:
        response = await ac.get("/mcp")
    assert response.status_code != 401


@pytest.mark.anyio
async def test_mcp_auth_missing_token_returns_jsonrpc_error(monkeypatch):
    """Without Authorization header, MCPAuthMiddleware returns the compliance JSON-RPC error."""
    import backend.middleware.mcp_auth as mcp_auth

    monkeypatch.setattr(mcp_auth, "_MCP_API_KEY", "secret-test-key")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/mcp", json={"jsonrpc": "2.0", "method": "ping", "id": 1})
    assert response.status_code == 401
    assert response.json() == JSONRPC_UNAUTH
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.anyio
async def test_mcp_auth_wrong_token_returns_jsonrpc_error(monkeypatch):
    """A wrong Bearer token returns the compliance JSON-RPC error."""
    import backend.middleware.mcp_auth as mcp_auth

    monkeypatch.setattr(mcp_auth, "_MCP_API_KEY", "correct-key")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "ping", "id": 1},
            headers={"Authorization": "Bearer wrong-key"},
        )
    assert response.status_code == 401
    assert response.json() == JSONRPC_UNAUTH


@pytest.mark.anyio
async def test_mcp_auth_valid_token_passes(monkeypatch):
    """A correct Bearer token passes through the middleware."""
    import backend.middleware.mcp_auth as mcp_auth
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    token = "valid-secret-key"
    monkeypatch.setattr(mcp_auth, "_MCP_API_KEY", token)

    async def mcp_stub(request):
        return JSONResponse({"ok": True})

    stub = Starlette(routes=[Route("/mcp", mcp_stub, methods=["GET", "POST"])])
    stub.add_middleware(mcp_auth.MCPAuthMiddleware)

    async with AsyncClient(
        transport=ASGITransport(app=stub), base_url="http://test"
    ) as ac:
        response = await ac.get("/mcp", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code != 401


@pytest.mark.anyio
async def test_non_mcp_path_unaffected(monkeypatch):
    """Non-/mcp paths are never blocked by MCPAuthMiddleware."""
    import backend.middleware.mcp_auth as mcp_auth

    monkeypatch.setattr(mcp_auth, "_MCP_API_KEY", "some-key")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
