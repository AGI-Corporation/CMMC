## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-12 - Information Leakage via Global Exception Handling
**Vulnerability:** Explicitly returning `str(e)` in `HTTPException` or allowing unhandled exceptions to propagate can leak sensitive internal details (stack traces, database schemas, or logic paths).
**Learning:** FastAPI's default error handling for unhandled exceptions returns a detailed response in debug mode and a less detailed one in production, but explicitly raised `HTTPException(detail=str(e))` will always leak. A global exception handler for both `StarletteHTTPException` (to mask 5xx) and the base `Exception` class ensures a consistent, secure "fail-closed" posture for error messages.
**Prevention:** Implement a global exception handler in `main.py` that logs the full error context internally but returns a generic message to the client. Avoid `try...except: raise HTTPException(detail=str(e))` patterns in routers.
