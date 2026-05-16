## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Information Disclosure via Explicit HTTPException
**Vulnerability:** API endpoints were explicitly catching internal exceptions and re-raising them as `HTTPException(status_code=500, detail=str(e))`, which leaked sensitive implementation details (database strings, file paths, etc.) to the client.
**Learning:** A global `Exception` handler in FastAPI does not automatically mask the `detail` of an explicitly raised `HTTPException`. Security-minded error handling requires a specific handler for `StarletteHTTPException` that checks the status code and overwrites the `detail` for 500+ errors.
**Prevention:** Avoid `detail=str(e)` in production code. Use a global `StarletteHTTPException` handler to enforce a standard, safe error message for all server-side failures while preserving informative 4xx messages.
