"""
Security Headers Middleware - Standard security hardening.
AGI Corporation 2026
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds standard security headers to all responses.
    Protects against common web vulnerabilities like clickjacking and MIME-sniffing.
    """
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)

        # Prevent clickjacking by forbidding framing
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Protect referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CSP: restrict where the site can be framed
        # For an API-first platform, we start strict
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"

        return response
