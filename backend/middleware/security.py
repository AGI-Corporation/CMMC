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
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Content Security Policy - defense-in-depth against XSS and clickjacking
        # default-src 'self' restricts all resources to the same origin by default
        # script-src and style-src allow 'unsafe-inline' to support FastAPI Swagger UI
        # img-src 'self' and data: allow local images and base64-encoded icons
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "img-src 'self' data: https://fastapi.tiangolo.com",
            "frame-ancestors 'none'",
            "connect-src 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Referrer Policy - only send referrer for same-origin requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
