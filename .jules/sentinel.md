## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Information Leakage via Agent Router Errors
**Vulnerability:** Mistral agent endpoints leaked raw exception details (e.g., `str(e)`) in 500 responses, potentially exposing database credentials or stack traces to clients.
**Learning:** Using `raise HTTPException(status_code=500, detail=str(e))` within local `try...except` blocks is an anti-pattern that prioritizes client debugging over security. Centralizing unhandled exception processing in a global FastAPI handler ensures a generic 'Internal server error' is returned while the full context is preserved in server-side logs.
**Prevention:** Avoid catching generic `Exception` in routers just to return them as HTTP 500s. Let unexpected errors bubble up to a global exception handler that masks sensitive details.
