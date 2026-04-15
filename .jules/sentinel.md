## 2026-04-15 - Error handling detail leakage in FastAPI
**Vulnerability:** The exception details were being logged explicitly and passed to users via `raise HTTPException(status_code=500, detail=str(e))`. This led to internal structure and potentially sensitive operational data to be inadvertently exposed to users.
**Learning:** Returning generic responses and suppressing complex error descriptions are a common best practice in API applications. When dealing with exceptions that might include full stack traces, server path locations or DB details we must use the standard error logging to log those issues securely for internal diagnosis and only show generic user facing messages to consumers of the API endpoints to limit potential information extraction.
**Prevention:** Avoid writing explicit `detail=str(e)` lines in endpoints catching generic Exception occurrences. Send standard, generic `HTTPException(status_code=500, detail="An internal server error occurred")` instead and use `logging.error(f"Error: {e}")` to correctly register those errors on the backend.

## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.
