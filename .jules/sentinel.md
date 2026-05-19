## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-02-24 - Global Exception Masking and Validation Errors
**Vulnerability:** Information disclosure via unhandled exceptions and explicit `detail=str(e)` in `HTTPException` constructors. This allowed internal implementation details (e.g., database errors, stack traces) to leak to API clients.
**Learning:** A global `Exception` handler in FastAPI catches everything, including `RequestValidationError`. If not handled carefully, it can inadvertently mask helpful 422 validation errors with generic 500 errors, degrading the developer experience and client-side error handling.
**Prevention:** Always implement specific handlers for `StarletteHTTPException` and `RequestValidationError` alongside a global `Exception` catch-all. Use `fastapi.exception_handlers.http_exception_handler` to preserve default behavior for non-server errors (4xx) while enforcing a masking policy for server-side errors (500+).
