# Sentinel Security Journal 🛡️

## 2025-05-15 - Standard Security Headers Middleware
**Vulnerability:** Lack of standard security headers (X-Frame-Options, X-Content-Type-Options, etc.) could leave the application vulnerable to clickjacking, MIME-sniffing, and other cross-origin attacks.
**Learning:** FastAPI's global middleware is an efficient place to enforce defense-in-depth headers across all API responses.
**Prevention:** Always include a security headers middleware in the main application entry point (`backend/main.py`) to ensure every response carries these protections.
