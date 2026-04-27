## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-20 - Global Exception Handler & Error Leakage Prevention
**Vulnerability:** Information leakage via raw exception strings in API responses. Multiple agent endpoints were catching generic `Exception` and returning `str(e)` in `HTTPException(detail=...)`, potentially exposing secrets or internal architecture.
**Learning:** In FastAPI, a global `@app.exception_handler(Exception)` can catch all unhandled errors to return a generic 500 response. However, it *must* explicitly handle `starlette.exceptions.HTTPException` and `fastapi.exceptions.RequestValidationError` by delegating to default handlers (using `http_exception_handler` and `request_validation_exception_handler`) to avoid masking legitimate 4xx client errors as 500 Internal Server Errors.
**Prevention:** Avoid `str(e)` in public-facing error messages. Use a global exception handler that logs `exc_info=True` for internal debugging but serves sanitized generic messages to the client.
