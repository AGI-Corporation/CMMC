from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security-related headers to all outgoing HTTP responses.
    This implements defense-in-depth measures to protect against common web vulnerabilities.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent clickjacking by denying the page to be displayed in a frame
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent the browser from MIME-sniffing the response
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Control how much referrer information the browser includes with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy: frame-ancestors 'none' is a modern replacement for X-Frame-Options
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"

        return response
