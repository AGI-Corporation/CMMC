## 2025-05-15 - [Latest Assessment Query Optimization]
**Learning:** Fetching the "latest record per group" (e.g., latest assessment per control) becomes a major bottleneck as the database grows. A composite index on `(group_id, date_field)` is essential for SQLite/PostgreSQL to efficiently handle the `MAX(date)` subquery pattern. Additionally, fetching assessments for *all* items when the user has filtered the primary list (e.g., by domain) is a common but avoidable source of overhead.

**Action:** Always use a composite index for "latest per group" patterns and pass filter IDs down to the database helper to avoid over-fetching assessment data.
