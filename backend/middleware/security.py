from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security-related headers to every response.
    This implements defense-in-depth by enforcing browser-side security policies.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Prevent clickjacking by forbidding the page from being rendered in a frame/iframe
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable browser XSS filtering (legacy, but still useful as a fallback)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control how much referrer information is passed when navigating away
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy: Limit where resources can be loaded from
        # 'unsafe-inline' is currently needed for FastAPI's default Swagger UI
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        )

        # HTTP Strict Transport Security: Enforce HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
