## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-04-14 - Information Leakage in API Exception Handling
**Vulnerability:** FastAPIs `HTTPException` endpoints (`/gap-analysis`, `/code-review`, `/ask`) were exposing raw internal exception details (`str(e)`) directly to clients on HTTP 500 errors.
**Learning:** Exposing raw exceptions (`str(e)`) in API responses is an information leakage risk because it can reveal sensitive system details, internal paths, configurations, or downstream dependencies (e.g., Mistral client errors) to external users. The application needs to securely log the internal stack trace without exposing it.
**Prevention:** Always log exceptions server-side using the `logging` module (`logging.error()`) and raise an `HTTPException` with a generic `detail` message (e.g., "An internal server error occurred.") to avoid leaking implementation details.
