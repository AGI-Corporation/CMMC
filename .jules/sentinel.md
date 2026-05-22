## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Global Error Masking and Exception Handling
**Vulnerability:** Internal information disclosure via error messages. Explicit `try...except` blocks in API routes returned `str(e)`, leaking internal implementation details (e.g., database connection strings, library internals) to end-users during failures.
**Learning:** Centralized exception handling is superior to per-route `try...except` blocks for security. FastAPI's dependency on Starlette means both `StarletteHTTPException` and generic `Exception` should be handled. Logging the full exception internally while returning a generic message to the client follows the "fail securely" principle.
**Prevention:** Avoid `detail=str(e)` in any `HTTPException`. Implement a global exception handler in the main application file to catch and mask all unhandled 500-level errors.
