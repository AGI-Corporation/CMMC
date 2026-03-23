## 2025-05-22 - Dependency Conflict and Error Masking
**Vulnerability:** Information Leakage in API errors and potential Denial of Service due to dependency version mismatch.
**Learning:** The `mistralai` package version 2.x breaks the `Mistral` client import used in the agent. Also, masking errors for security (returning generic messages) without server-side logging makes systems unmaintainable.
**Prevention:** Pin critical AI dependencies to specific versions. Always use `logger.exception()` or `logger.error(..., exc_info=True)` when catching all Exceptions to ensure the root cause is captured in logs while keeping the client response safe.
