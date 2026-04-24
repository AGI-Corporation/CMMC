## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-05-20 - Information Exposure in Mistral Agent Endpoints
**Vulnerability:** FastAPIs HTTPExceptions were catching generic Exceptions and returning `str(e)` directly to the client. This CWE-209 vulnerability could leak internal system paths, configuration details, or third-party API errors in a 500 status response.
**Learning:** Returning raw exception strings directly via API endpoints is a common pattern to avoid, especially when interacting with complex external services like Mistral or Codestral, whose errors may include internal headers or data.
**Prevention:** Catch generic exceptions, log them internally using `logging.error("...", exc_info=True)` for debuggability, and return a sanitized, generic error message (e.g., "Internal server error") to the external client.
