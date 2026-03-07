## 2026-05-24 - Missing Security Headers in FastAPI Backend
**Vulnerability:** The FastAPI backend was missing standard security headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and CSP frame-ancestors), making the application vulnerable to clickjacking and MIME-sniffing attacks.
**Learning:** Modern web frameworks like FastAPI do not include these security headers by default. For compliance-heavy applications (like CMMC), defense-in-depth requires explicit implementation of these headers at the middleware level.
**Prevention:** Always implement a security middleware to inject these headers or use a library like `secure` to handle standard security headers automatically.
