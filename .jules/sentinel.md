## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-20 - Global Error Masking and Exception Handling
**Vulnerability:** Information Exposure through Error Messages (CWE-209). Explicit use of `detail=str(e)` in `HTTPException` and lack of a global catch-all handler allowed internal system details and stack traces to leak to API consumers.
**Learning:** FastAPI's default error handling can be too verbose for production. A robust defense-in-depth strategy requires both removing explicit leaks (like `str(e)`) and implementing a global exception handler. When implementing the handler, it is critical to distinguish between `StarletteHTTPException` (to preserve intended 4xx client errors) and generic `Exception` (to mask unexpected 500 server errors).
**Prevention:** Use a global exception handler to unify error responses. Never pass raw exception strings to the client. Audit codebase for `str(e)` or `repr(e)` in API responses.
