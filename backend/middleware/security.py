"""
Security Headers Middleware for FastAPI
AGI Corporation 2026

Implements standard security headers to protect against common web vulnerabilities.
- X-Frame-Options: Protects against clickjacking
- X-Content-Type-Options: Prevents MIME-sniffing
- Referrer-Policy: Controls how much referrer information is shared
- Content-Security-Policy: Mitigates XSS and data injection attacks
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)

        # 🛡️ Sentinel: Standard Security Headers

        # Prevent clickjacking by disallowing the page from being rendered in an iframe
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy - strictly control where resources can be loaded from
        # Note: 'frame-ancestors none' is equivalent to X-Frame-Options: DENY
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none';"

        return response
