"""
Security Headers Middleware - Sentinel Defense Layer
AGI Corporation 2026

Implements standard security headers to protect against clickjacking,
MIME-type sniffing, and other common web vulnerabilities.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 🛡️ Sentinel: Hardening headers

        # Prevent Clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (CSP) - Minimal frame protection
        # Using frame-ancestors 'none' to reinforce X-Frame-Options: DENY
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"

        return response
