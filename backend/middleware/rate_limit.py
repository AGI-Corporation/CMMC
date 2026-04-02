"""
Rate Limiting Middleware — CMMC Compliance Platform
AGI Corporation 2026

Sliding-window in-memory rate limiter. Uses the client's IP address as the
rate-limit key. Default: 200 requests per 60-second window per IP.

Environment variables:
    RATE_LIMIT_REQUESTS   — Max requests per window (default: 200).
    RATE_LIMIT_WINDOW_SEC — Window length in seconds (default: 60).

Testing helpers:
    reset_all_windows()   — Clear all rate-limit windows (used in test setUp).
"""

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "200"))
_WINDOW_SEC: int = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))

# ---------------------------------------------------------------------------
# Sliding window storage: IP → deque of request timestamps
# ---------------------------------------------------------------------------

_windows: Dict[str, Deque[float]] = defaultdict(deque)


def reset_all_windows() -> None:
    """
    Clear all rate-limit tracking windows.

    Designed to be called from test fixtures before each test to prevent
    cumulative request counts from triggering 429 responses.
    """
    _windows.clear()


def _get_client_ip(request: Request) -> str:
    """Extract the best-available client IP from request headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ---------------------------------------------------------------------------
# Middleware class
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter middleware.

    Returns HTTP 429 with Retry-After header when a client exceeds the
    configured request limit within the rolling window.
    """

    async def dispatch(self, request: Request, call_next):
        ip = _get_client_ip(request)
        now = time.monotonic()
        window_start = now - _WINDOW_SEC

        dq = _windows[ip]

        # Evict timestamps older than the current window
        while dq and dq[0] < window_start:
            dq.popleft()

        if len(dq) >= _MAX_REQUESTS:
            retry_after = int(_WINDOW_SEC - (now - dq[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        dq.append(now)
        response: Response = await call_next(request)
        return response
