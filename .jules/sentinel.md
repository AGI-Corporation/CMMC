## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Global Exception Handling for Information Disclosure Prevention
**Vulnerability:** Information Disclosure via Error Messages (CWE-209). Endpoints leaking raw exception strings (e.g., `str(e)`) could expose internal state, database connection details, or sensitive logic to attackers.
**Learning:** FastAPI's default behavior for unhandled exceptions returns plain text "Internal Server Error". By implementing a global `@app.exception_handler(Exception)`, we can enforce a consistent JSON response and centralize security logging with `exc_info=True`. It is critical to explicitly re-raise or exclude `HTTPException` and `RequestValidationError` from the global handler to preserve standard API functionality.
**Prevention:** Never return raw exception messages to clients. Use a global exception handler to mask unhandled errors and log details server-side only. Sanitize all `HTTPException` detail fields to ensure they contain only safe, user-facing messages.
