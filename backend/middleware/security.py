"""
Security Headers Middleware for CMMC Compliance Platform.
AGI Corporation 2026

Adds standard security headers to all responses to protect against
common web vulnerabilities (clickjacking, MIME sniffing, etc).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)

        # 🛡️ Sentinel: Defense in Depth - Add Security Headers

        # Prevent clickjacking by forbidding framing
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (Basic) - prevent framing
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"

        return response
