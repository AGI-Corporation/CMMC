## 2025-05-15 - [Database Indexing for Greatest-N-Per-Group]
**Learning:** In SQLite, a composite index on `(foreign_key, date_column)` significantly optimizes queries that use `GROUP BY foreign_key` and `MAX(date_column)` to find the latest record per group. This pattern is prevalent in compliance applications for tracking the most recent assessment state.
**Action:** Always check for redundant "latest record" subqueries in routers and centralize them into a helper that leverages composite indices.

## 2025-05-15 - [Filtering at the Database Level vs Python]
**Learning:** Even with an index, fetching 500 records and filtering them in Python is slower than filtering by ID in the database query if the subset is small (e.g., < 10% of total).
**Action:** Implement optional ID-based filtering in shared database helpers to allow routers to only fetch what they need.
