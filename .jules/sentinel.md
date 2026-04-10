## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.
## 2026-04-10 - Prevent Information Leakage in Mistral Agent API
**Vulnerability:** The `agents/mistral_agent/agent.py` file contained `except Exception as e:` blocks that directly returned `str(e)` in 500 HTTP responses. This can leak sensitive internal system details, API keys embedded in third-party service errors, or internal network structure.
**Learning:** Returning raw exception messages to the client is a common Information Exposure vulnerability (CWE-209). FastAPI's `HTTPException` detail parameter is directly passed to the client and should be sanitized.
**Prevention:** Always log the actual exception internally using `logging.error()` and return a generic, static message like 'An internal server error occurred.' to external clients when handling generic 500 errors.
