from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds standard security headers to all HTTP responses.
    Provides defense-in-depth against common web vulnerabilities.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent clickjacking by not allowing the site to be embedded in an iframe
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent browsers from MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS filtering in browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS (HSTS) - 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy - restrict where the site can be embedded
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"

        # Referrer Policy - only send referrer for same-origin requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
