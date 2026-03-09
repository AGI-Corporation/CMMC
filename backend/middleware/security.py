from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds standard security headers to all outgoing responses.

    - X-Frame-Options: DENY (prevents clickjacking)
    - X-Content-Type-Options: nosniff (prevents MIME sniffing)
    - Referrer-Policy: strict-origin-when-cross-origin (controls referrer information)
    - Content-Security-Policy: frame-ancestors 'none'; (modern alternative to X-Frame-Options)
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"
        return response
