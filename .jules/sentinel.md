## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.
## 2026-05-20 - Prevent Information Exposure via HTTP 500 Responses
**Vulnerability:** The `/gap-analysis`, `/code-review`, and `/ask` endpoints in the Mistral Agent (`agents/mistral_agent/agent.py`) were exposing raw exception details (`str(e)`) directly to the client in HTTP 500 responses (CWE-209).
**Learning:** Exposing full stack traces or exception strings can leak sensitive internal state, configuration details, or API keys to potentially malicious actors. Internal services should fail securely and provide generic error messages to clients.
**Prevention:** Always log the exception server-side using `logging.error("...", exc_info=True)` for debuggability, and return a sanitized, generic error string (e.g., "Internal server error") in the HTTP response.
