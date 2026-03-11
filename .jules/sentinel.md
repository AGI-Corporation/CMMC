## 2026-02-28 - [Mistral AI SDK Version Conflict]
**Vulnerability:** The `mistralai` Python SDK was unpinned, and version 2.0.0 introduced breaking changes that caused the application to fail during initialization.
**Learning:** Version 2.0.0 of `mistralai` has a different import structure and client initialization than 1.1.0, which the current agent logic depends on.
**Prevention:** Always pin core AI dependencies to specific versions and verify with tests after any environment changes.
