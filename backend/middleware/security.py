"""
Security Middleware for adding common security headers.
AGI Corporation 2026
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds common security headers to every response.
    Protects against clickjacking, MIME-sniffing, and more.
    """
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)

        # Prevent the site from being embedded in iframes (Clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent the browser from interpreting files as a different MIME type (MIME-sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Control how much referrer information is sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Basic Content Security Policy to prevent framing
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"

        return response
