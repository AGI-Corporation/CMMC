## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-20 - Sensitive Information Leakage in Error Responses
**Vulnerability:** API endpoints were leaking internal exception details (e.g., stack traces, database error messages) to clients via `raise HTTPException(detail=str(e))`.
**Learning:** Relying on per-endpoint `try...except` blocks for 500-level errors is error-prone and often leads to inadvertent information disclosure. FastAPI's default behavior for unhandled exceptions can also expose details if not properly managed.
**Prevention:** Implement a global exception handler (`@app.exception_handler(Exception)`) to mask unexpected errors with a generic message while logging the full traceback on the server. Always separate client-facing error messages from internal diagnostic logs.
