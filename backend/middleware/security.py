from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers for defense-in-depth
        # Prevents clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Prevents MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Controls referrer information sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy: frame-ancestors 'none' for modern clickjacking protection
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"

        return response
