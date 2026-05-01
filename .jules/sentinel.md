## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-20 - Global Exception Handling for Error Leakage Prevention
**Vulnerability:** Individual agent routes were explicitly catching exceptions and returning `str(e)` in HTTP 500 responses, which leaked sensitive internal information (e.g., database details, API errors) to clients.
**Learning:** Returning raw exception messages in a REST API is an information disclosure risk. FastAPI's default error handling can be enhanced with a global exception handler that logs full tracebacks server-side while returning a generic "Internal server error" to the user, providing both visibility and security.
**Prevention:** Never use `detail=str(e)` in `HTTPException`. Refactor routes to allow unexpected errors to bubble up to a global handler, and implement specific handlers for standard exceptions (like `StarletteHTTPException`) to preserve intended 4xx responses.
