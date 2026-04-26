## 2026-05-20 - Information Exposure in Exception Handling
**Vulnerability:** FastAPIs HTTPException returned raw stringified exceptions (`str(e)`) to the client on internal server errors.
**Learning:** This exposes internal configurations, connection strings, or system paths from underlying dependency errors to end users, a direct CWE-209 vulnerability.
**Prevention:** Always log the exception safely with `logging.error("...", exc_info=True)` and return a generic user-safe status message for 500 status codes.
