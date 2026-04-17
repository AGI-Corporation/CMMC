## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - Information Leakage in Mistral Agent Endpoints
**Vulnerability:** The Mistral AI agent FastAPI endpoints (`/gap-analysis`, `/code-review`, `/ask`) in `agents/mistral_agent/agent.py` caught generic exceptions and raised HTTP 500 errors with `detail=str(e)`. This leaked internal error messages and potential stack details to external clients.
**Learning:** Returning raw exception strings directly to users via HTTP error responses is a security risk, as it can expose system architecture, API keys, or database states.
**Prevention:** Always log exceptions internally using `logging.error(..., exc_info=True)` and return a sanitized, generic error message (e.g., "Internal server error") to the client.
