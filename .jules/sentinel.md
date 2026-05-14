## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-14 - Internal Error Detail Leakage in Agent Routes
**Vulnerability:** API endpoints in the Mistral agent were using `try...except` blocks that explicitly returned `str(e)` in the `HTTPException` detail, leaking internal implementation details (e.g., database paths, library error messages) to clients on failure.
**Learning:** Explicitly catching all exceptions to return them in the response is a common anti-pattern that defeats secure global error handling. FastAPI's default behavior can also leak details if not properly configured with a global exception handler.
**Prevention:** Avoid `try...except` blocks that re-raise with raw exception strings in route handlers. Implement a global exception handler for the `Exception` class and `StarletteHTTPException` (for status >= 500) to mask internal details while preserving informative 4xx errors for clients.
