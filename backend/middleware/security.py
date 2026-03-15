from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to every response.
    - X-Frame-Options: DENY (Prevents clickjacking)
    - X-Content-Type-Options: nosniff (Prevents MIME-type sniffing)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: frame-ancestors 'none'
    """
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response
