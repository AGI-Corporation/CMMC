## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Centralized Error Masking in FastAPI
**Vulnerability:** Internal error leakage via `HTTPException(status_code=500, detail=str(e))` and unhandled exceptions across agent routers.
**Learning:** Local `try...except` blocks that return `str(e)` in API responses are a primary source of information leakage (CWE-209). FastAPI's default behavior preserves `HTTPException` details even for 500 errors, and unhandled exceptions can leak internals if not globally masked.
**Prevention:** Implement a centralized `Exception` handler in `backend/main.py` that masks all 500+ errors with a generic "Internal server error" message while preserving informative 4xx/422 messages. Use `httpx.AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False))` in tests to verify masking logic.
