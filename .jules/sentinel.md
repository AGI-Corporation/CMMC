## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-20 - Information Exposure (CWE-209) in API error responses
**Vulnerability:** Fast API exception handling using `detail=str(e)` on generic `Exception` blocks in `agents/mistral_agent/agent.py` was directly returning Python error messages to external callers.
**Learning:** Returning exception details from `try...except Exception as e` directly exposes internal state, network traces, or API keys (if an HTTP failure occurs) directly to end users.
**Prevention:** Always log exceptions internally using `logging.error("msg", exc_info=True)` and return a sanitized, generic error detail (`An internal server error occurred.`) to the client to implement proper defense-in-depth against Information Disclosure.
