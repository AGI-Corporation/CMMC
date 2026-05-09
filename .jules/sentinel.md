## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-09 - Global Exception Masking in FastAPI
**Vulnerability:** Information Exposure (CWE-209) through leaking internal exception details (e.g., stack traces, database strings) via `HTTPException(detail=str(e))`.
**Learning:** FastAPI's default error handling can be overridden with `@app.exception_handler(Exception)`. To avoid masking legitimate 4xx errors, a specialized handler for `StarletteHTTPException` must be registered first. For testing, `AsyncClient` must use `raise_app_exceptions=False` to verify the handler's output rather than letting the exception bubble into the test runner.
**Prevention:** Avoid local `try...except` blocks that re-raise exceptions with `str(e)`. Use a global exception handler to mask all 500-level errors with a generic message.
