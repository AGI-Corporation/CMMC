## 2026-03-05 - [Composite Index for Latest Assessments]
**Learning:** The 'latest-per-group' query pattern (fetching the most recent assessment for each control) is a common bottleneck when the number of assessments grows. Using a composite index on `(control_id, assessment_date)` significantly optimizes this pattern by allowing the database to efficiently find the maximum date within each control group.
**Action:** Always check for 'latest-per-group' query patterns in compliance/audit apps and implement composite indices on the grouping and ordering columns.

## 2026-03-05 - [SDK Version Compatibility]
**Learning:** Upgrading or changing SDK usage (like Mistral AI) can introduce subtle breaking changes if the environment has a different version than expected. v1.x and v2.x of the `mistralai` library have different client classes (`MistralClient` vs `Mistral`) and method names (`chat_async` vs `chat.complete_async`).
**Action:** Always verify the installed package version (`pip show`) and test the exact import path before refactoring SDK-related code. Restore modern patterns if they were accidentally reverted during environment troubleshooting.
