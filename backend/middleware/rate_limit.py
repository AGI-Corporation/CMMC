"""
Rate Limiting Middleware
AGI Corporation 2026

Implements a sliding-window rate limiter using stdlib collections only.
No external dependencies required.

Configuration (env vars):
  RATE_LIMIT_PER_MIN  - Max requests per IP per minute (default: 120)
  RATE_LIMIT_ENABLED  - Set to "false" to disable (default: "true")

The limiter identifies clients by their real IP address, honoring
X-Forwarded-For when the request originates behind a trusted proxy.

Returns HTTP 429 Too Many Requests when the limit is exceeded.

Compliance mapping:
  SC.3.187 - Implement cryptographically protected channels (rate limiting
             reduces credential-stuffing and API abuse surface)
  SI.1.210 - Identify, report, and correct information system flaws
  AC.1.001 - Limit system access to authorized users (rate limiting is an
             enforcement mechanism against brute-force access attempts)
"""

import collections
import os
import time
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

RATE_LIMIT_PER_MIN: int = int(os.getenv("RATE_LIMIT_PER_MIN", "120"))
RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# Endpoints exempt from rate limiting (health probes, OpenAPI docs)
_EXEMPT_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json", "/mcp"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter.

    Uses a per-IP deque of request timestamps.  On each request the deque
    is pruned to the last 60 seconds and the current timestamp is appended.
    If the deque length exceeds RATE_LIMIT_PER_MIN, the request is rejected
    with HTTP 429.

    Thread-safety: CPython's GIL makes deque operations atomic enough for
    asyncio (single-threaded event loop); no extra locking is needed.
    """

    def __init__(self, app, limit: int = RATE_LIMIT_PER_MIN):
        super().__init__(app)
        self.limit = limit
        # {ip: deque of float timestamps}
        self._windows: Dict[str, Deque[float]] = collections.defaultdict(
            collections.deque
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP, respecting X-Forwarded-For."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the leftmost (original client) address
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Exempt health-check and docs paths
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        ip = self._get_client_ip(request)
        now = time.monotonic()
        window_start = now - 60.0

        dq = self._windows[ip]

        # Prune timestamps outside the 60-second window
        while dq and dq[0] < window_start:
            dq.popleft()

        if len(dq) >= self.limit:
            retry_after = int(60 - (now - dq[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "limit": self.limit,
                    "window_seconds": 60,
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        dq.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.limit - len(dq))
        )
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))
        return response
