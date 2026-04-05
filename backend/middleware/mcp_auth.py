"""
MCP Bearer Token Authentication Middleware
AGI Corporation 2026

Guards the /mcp endpoint with Bearer token authentication.
Unauthorized requests receive the standard JSON-RPC 2.0 error response:

    {"jsonrpc":"2.0","error":{"code":-32001,"message":"Unauthorized — Bearer token required"},"id":null}

This error format is the compliance reference for MCP API authentication
requirements, mapped to CMMC IA.1.076 and IA.1.077 (authenticate users
before allowing access to information systems).

Set MCP_API_KEY env var to enable enforcement. If unset, the middleware
allows all requests (development mode) and logs a warning.
"""

import json
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Compliance reference: the canonical JSON-RPC 2.0 error returned to any
# caller that reaches /mcp without a valid Bearer token.  This exact payload
# is registered as an evidence artifact for IA.1.077.
JSONRPC_UNAUTHORIZED: dict = {
    "jsonrpc": "2.0",
    "error": {
        "code": -32001,
        "message": "Unauthorized \u2014 Bearer token required",
    },
    "id": None,
}

_MCP_API_KEY: str = os.getenv("MCP_API_KEY", "")

if not _MCP_API_KEY:
    import warnings

    warnings.warn(
        "MCP_API_KEY is not set — /mcp endpoint is unauthenticated (development mode). "
        "Set MCP_API_KEY in production to enforce CMMC IA.1.077 compliance.",
        stacklevel=2,
    )


def _unauthorized_response() -> Response:
    return Response(
        content=json.dumps(JSONRPC_UNAUTHORIZED),
        status_code=401,
        media_type="application/json",
        headers={"WWW-Authenticate": "Bearer"},
    )


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that enforces Bearer token authentication on all
    requests to the /mcp path.

    CMMC Controls addressed:
      • IA.1.076 — Identify information system users, processes, or devices
      • IA.1.077 — Authenticate (or verify) the identities of those users,
                   processes, or devices as a prerequisite to allowing access

    ZT Pillar: User / Visibility & Analytics
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)

        # If no key is configured, allow through (dev mode).
        if not _MCP_API_KEY:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _unauthorized_response()

        token = auth_header[len("Bearer "):].strip()
        if not secrets.compare_digest(token, _MCP_API_KEY):
            return _unauthorized_response()

        return await call_next(request)
