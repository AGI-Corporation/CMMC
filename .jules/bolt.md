## 2026-05-15 - [Composite Indexing & DB-level Filtering]
**Learning:** Found that the `list_controls` endpoint was performing O(N) Python-side filtering and multiple DB roundtrips. By introducing a composite index on `(control_id, assessment_date)` and refactoring the query to use a single SQL JOIN with subqueries, we moved the heavy lifting to the database engine.
**Action:** Always check for opportunities to replace Python-side filtering with DB-level `WHERE` clauses and ensure supporting indexes (especially composite ones for temporal lookups) are present.
