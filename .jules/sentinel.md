## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Centralized Error Handling to Prevent Information Leakage
**Vulnerability:** API endpoints were catching exceptions and returning the raw error message (`str(e)`) to clients. This could leak sensitive internal state, database structure, or API keys (CWE-209).
**Learning:** Manually catching exceptions in routers and returning them in `HTTPException` is a security risk. FastAPI's global exception handler (`@app.exception_handler(Exception)`) should be used to log the full traceback internally while returning a generic "Internal server error" to the client.
**Prevention:** Avoid using `str(e)` in client-facing error messages. Implement a global exception handler and let unhandled exceptions bubble up to it. Ensure that standard FastAPI 4xx responses are preserved by explicitly handling `StarletteHTTPException` and `RequestValidationError` in the global handler.
