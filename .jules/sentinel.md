## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-16 - Information Leakage via Error Messages
**Vulnerability:** Agent router endpoints were leaking sensitive internal details (e.g., database errors, stack traces) by returning `str(e)` in `HTTPException` details. Additionally, the application lacked a global exception handler, meaning unhandled exceptions could also leak internals in default 500 responses.
**Learning:** Returning raw exception messages to the client is a high-risk information leakage pattern. While FastAPI provides some default handling, it doesn't automatically sanitize all unhandled exceptions in a production-safe way without a custom global handler. Explicitly catching exceptions in routes and returning generic messages is necessary but should be complemented by a global handler for unexpected failures.
**Prevention:** 1. Implement a global exception handler in `backend/main.py` using `@app.exception_handler(Exception)` that logs the full traceback but returns a generic "Internal server error". 2. Avoid using `str(e)` in `HTTPException` details; use user-friendly, non-revealing messages instead. 3. Ensure the global handler preserves standard 4xx responses by checking for `HTTPException` and `RequestValidationError`.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.
