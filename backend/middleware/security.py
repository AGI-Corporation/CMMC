"""
Security Headers Middleware for FastAPI
AGI Corporation 2026

Adds standard security headers to all outgoing responses to enhance defense-in-depth.
Includes: X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and CSP.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)

        # Prevent clickjacking by disallowing framing
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Control referrer information sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy - frame-ancestors 'none' for further clickjacking protection
        # For a full CSP, we would need to know the allowed origins for scripts, styles, etc.
        # But setting frame-ancestors is a safe and high-impact baseline.
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"

        return response
