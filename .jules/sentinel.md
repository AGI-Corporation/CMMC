## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-03-10 - Secure Global Exception Handling
**Vulnerability:** Information leakage through verbose error messages. Multiple endpoints were catching generic exceptions and re-raising them as `HTTPException(status_code=500, detail=str(e))`, exposing internal system details to clients.
**Learning:** While FastAPI provides some default error masking, explicitly raising `str(e)` in the `detail` field bypasses these protections. A centralized `@app.exception_handler(Exception)` is necessary to ensure a consistent, secure "fail-closed" posture. It must explicitly delegate to `http_exception_handler` and `request_validation_exception_handler` to avoid masking legitimate 4xx client errors (404, 422) as 500s.
**Prevention:** Avoid `detail=str(e)` in all routers. Use a global exception handler to catch unhandled errors, log them with `exc_info=True` for internal debugging, and return generic messages to the user.
