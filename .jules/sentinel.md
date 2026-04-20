## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Sensitive Information Leakage in Error Messages
**Vulnerability:** The application was leaking internal error details (such as database connection strings or stack traces) via HTTP 500 responses. This was primarily due to `try-except` blocks in API routers that caught exceptions and re-raised them with `detail=str(e)`.
**Learning:** Catching broad exceptions and returning the string representation of the exception to the client is a security risk. FastAPI's default behavior can also expose details if not properly managed. A centralized global exception handler is required to sanitize error responses.
**Prevention:** Implement a global `@app.exception_handler(Exception)` in FastAPI. This handler should log full details internally for developers but return a generic message (e.g., "Internal server error") to the client. Ensure the handler also preserves legitimate 4xx responses by explicitly checking for and delegating `HTTPException` and `RequestValidationError`.
