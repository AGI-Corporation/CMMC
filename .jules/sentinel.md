## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-13 - Secure Error Handling & Information Disclosure Mitigation
**Vulnerability:** Endpoints were explicitly returning raw exception strings (`str(e)`) to clients, risking the disclosure of sensitive internal state (e.g., database connection details, stack traces).
**Learning:** Explicitly raising `HTTPException(status_code=500, detail=str(e))` bypasses many default security assumptions. Removing local error trapping in favor of a global exception handler in `main.py` ensures that all internal server errors are consistently masked with a generic message while maintaining internal visibility via server-side logging.
**Prevention:** Avoid catching generic exceptions just to re-raise them with the error message in the response. Implement a global `app.exception_handler(Exception)` and `app.exception_handler(StarletteHTTPException)` to intercept and sanitize 500+ errors application-wide.
