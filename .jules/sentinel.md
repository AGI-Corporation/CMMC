## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-04-05 - [Exception Details Exposed in API Responses]
**Vulnerability:** In `agents/mistral_agent/agent.py`, catching exceptions and using `str(e)` directly in the `HTTPException` detail exposes internal error information, stack traces, and underlying API failures to the user.
**Learning:** Developers might find it helpful for debugging to directly surface raw errors through API endpoints, but this inherently leaks sensitive internal structure and details of the underlying processes.
**Prevention:** Catch exceptions globally or per-endpoint, log the detailed error with `logging.error()`, and return a generic 500 status message (e.g., "An internal server error occurred") to external clients.
