## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Information Leakage via Error Messages
**Vulnerability:** Unhandled exceptions and catch-all `raise HTTPException(status_code=500, detail=str(e))` patterns were leaking internal system details (DB credentials, file paths, stack traces) to API clients.
**Learning:** Default error handling in FastAPI can expose internals if not explicitly managed. Catching exceptions and returning `str(e)` is dangerous as it might contain sensitive data from lower-level libraries.
**Prevention:** Use a global exception handler in `backend/main.py` to catch all unhandled `Exception`s and return a generic "Internal server error". In local endpoint handlers, log the actual exception server-side and return masked, generic error messages to the user.
