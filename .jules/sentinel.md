## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Global Error Masking and Exception Handling
**Vulnerability:** Internal error details and stack traces were leaked to clients via `HTTPException(detail=str(e))`, potentially exposing sensitive system information.
**Learning:** Catching all exceptions at the router level and returning `str(e)` is insecure. FastAPI's global exception handlers can be used to log full details on the server while returning a generic "Internal server error" to the client. Specialized handlers for `StarletteHTTPException` are necessary to prevent masking intended 4xx client errors.
**Prevention:** Use a global exception handler for `Exception` to mask unhandled errors. Never use `str(e)` or `repr(e)` in error responses sent to clients.
