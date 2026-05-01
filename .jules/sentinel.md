## 2025-05-15 - Security Headers Middleware Implementation
**Vulnerability:** Lack of defense-in-depth headers (X-Frame-Options, CSP, HSTS, etc.) made the application susceptible to clickjacking, MIME-sniffing, and protocol downgrade attacks.
**Learning:** FastAPI/Starlette does not include these headers by default. Implementing them via `BaseHTTPMiddleware` provides a central way to enforce browser-side security policies across all endpoints. The CSP was specifically tuned to allow `'unsafe-inline'` for script and style to support the FastAPI Swagger UI without breaking functionality.
**Prevention:** Always include a security headers middleware in FastAPI projects and regularly review CSP directives as the application evolves.

## 2025-05-15 - MistralAI Dependency Conflict
**Vulnerability:** Not a direct security vulnerability, but an environmental instability. The `requirements.txt` allowed `mistralai>=1.1.0`, which pulled in version 2.x.
**Learning:** MistralAI 2.x introduces breaking changes in the client import structure (`from mistralai import Mistral` fails if not using the new client correctly or if expecting the old one). This caused the entire application (including security tests) to fail on startup.
**Prevention:** Pin critical dependencies like `mistralai==1.1.0` in `requirements.txt` to ensure consistent behavior across development and CI environments, especially when using agents that rely on specific API structures.

## 2025-05-15 - HTTP Header Injection and Path Traversal in File Download
**Vulnerability:** The `/poam` endpoint used unsanitized user input (`system_name`) directly in the `Content-Disposition` header's `filename` attribute. This allowed for HTTP Header Injection and potential Path Traversal by inserting characters like `\r\n` or `../`.
**Learning:** Using simple string replacement (`replace(" ", "_")`) is insufficient for sanitizing user input that ends up in HTTP headers or file paths. Attackers can bypass this with other dangerous characters.
**Prevention:** Always validate and strictly sanitize user input used in HTTP headers or file paths using a whitelist approach (e.g., regex `re.sub(r'[^a-zA-Z0-9_\-]', '_', input)`) to ensure only safe characters are included.
