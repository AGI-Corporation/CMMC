## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - Global Exception Handling for Information Leakage Prevention
**Vulnerability:** API endpoints were returning raw exception messages (`str(e)`) to clients, potentially exposing sensitive internal details like database credentials or system paths.
**Learning:** FastAPI's default error handling can be too verbose in production. A global exception handler using `@app.exception_handler(Exception)` provides a "fail-secure" mechanism to ensure all unhandled errors return a generic message, while contextual logging in routers preserves debugability for developers.
**Prevention:** Implement a catch-all exception handler in the main application and avoid passing raw exception strings directly to `HTTPException`. Use logging with `exc_info=True` to capture full stack traces server-side only.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.
