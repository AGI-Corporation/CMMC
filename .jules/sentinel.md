## 2026-03-05 - Mistral Agent Version Compatibility
**Vulnerability:** Dependency mismatch causing system-wide `ImportError`.
**Learning:** The `mistralai` library version 2.x introduces breaking changes to the `Mistral` client import that are incompatible with current agent implementations.
**Prevention:** Always pin core AI dependencies to specific versions in `requirements.txt` to prevent breaking changes from upstream updates.

## 2026-03-05 - Verbose Error Leakage in AI Agents
**Vulnerability:** Information disclosure via detailed stack traces in HTTP 500 responses.
**Learning:** Using `str(e)` in exception handling for API responses can leak internal server state, file paths, and logic to potential attackers.
**Prevention:** Implement generic error messages for production API endpoints and log details internally only.
