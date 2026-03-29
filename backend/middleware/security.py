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

        # Content Security Policy - restrict where the site can be embedded and where resources can be loaded from
        # default-src 'self' allows resources from the same origin
        # script-src 'self' 'unsafe-inline' allows scripts from the same origin and inline scripts (needed for Swagger UI)
        # style-src 'self' 'unsafe-inline' allows styles from the same origin and inline styles (needed for Swagger UI)
        # img-src 'self' data: allows images from the same origin and data URIs
        # frame-ancestors 'none' prevents the site from being embedded in an iframe
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        )

        # Referrer Policy - only send referrer for same-origin requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
