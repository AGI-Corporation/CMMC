## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2026-04-16 - Information Leakage via HTTPException
**Vulnerability:** Explicitly passing 'str(e)' to 'HTTPException(status_code=500, ...)' leaked internal implementation details, such as API error messages and potential stack trace snippets, to the client.
**Learning:** Even with a global exception handler, manual 'try...except' blocks that re-raise 'HTTPException' with internal error strings will bypass the global handler's sanitization because 'HTTPException' is often explicitly allowed to pass through to preserve 4xx errors.
**Prevention:** Avoid 'str(e)' in 'HTTPException' details for 500 errors. Prefer a generic message and rely on centralized logging for debugging. Ensure the global exception handler specifically handles 'Exception' while delegating known 'HTTPException' cases safely.
