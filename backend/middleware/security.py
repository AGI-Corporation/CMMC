"""
Security Headers Middleware - Defense in Depth
AGI Corporation 2026

Adds standard security headers to all FastAPI responses to protect against
clickjacking, MIME-type sniffing, and other common web vulnerabilities.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # 🛡️ Prevents clickjacking by forbidding the site to be framed
        response.headers["X-Frame-Options"] = "DENY"

        # 🛡️ Prevents MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 🛡️ Controls how much referrer information is passed
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 🛡️ Content Security Policy - restricts frame-ancestors
        # This is a base CSP that can be expanded as needed
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"

        return response
