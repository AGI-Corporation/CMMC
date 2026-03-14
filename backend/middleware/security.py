"""
Security Middleware for CMMC Compliance Platform.
AGI Corporation 2026

Adds standard security headers to all responses.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Basic Content Security Policy
        # frame-ancestors 'none' is equivalent to X-Frame-Options DENY
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"

        return response
