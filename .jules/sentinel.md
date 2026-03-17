## 2026-03-05 - Security Headers Hardening
**Vulnerability:** Missing standard security headers (X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy).
**Learning:** Even with an AI-focused backend, basic web security headers are essential to prevent clickjacking and other common browser-based attacks when the API is consumed by a frontend.
**Prevention:** Always implement a security middleware that enforces these headers by default across all routes.
