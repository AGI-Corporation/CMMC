## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Global Exception Masking for Information Disclosure Prevention
**Vulnerability:** API endpoints were explicitly catching internal exceptions and returning the raw error message (`str(e)`) in the response detail. This leaked sensitive implementation details, internal state, and potentially database connection errors to clients.
**Learning:** FastAPI's default error handling can be bypassed by manual `try...except` blocks that re-raise `HTTPException`. A robust defense-in-depth approach requires both removing insecure localized error handling and implementing a global exception handler.
**Prevention:** Avoid `detail=str(e)` in `HTTPException`. Implement a global exception handler for `Exception` that logs tracebacks internally but returns a generic "An unexpected error occurred" message for all 500+ errors. Use specialized handlers for `StarletteHTTPException` and `RequestValidationError` to preserve useful 4xx and 422 feedback.
