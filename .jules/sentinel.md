## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.
## 2026-05-02 - Information Exposure via API Error Responses
**Vulnerability:** Information Exposure Through an Error Message (CWE-209) in `agents/mistral_agent/agent.py`. Endpoints were catching exceptions and passing the raw `str(e)` detail to the client via `HTTPException`.
**Learning:** Returning raw exception strings in API responses can leak sensitive internal system details (e.g., file paths, database structures, third-party API errors) to attackers.
**Prevention:** Always log the full exception detail internally using `logging.error(..., exc_info=True)` for debugging, and return a sanitized, generic error message (e.g., 'An internal error occurred') to the client.
