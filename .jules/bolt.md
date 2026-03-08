## 2026-03-08 - [Optimizing Latest-Per-Group Lookups]
**Learning:** Performing "latest per group" lookups in application memory is a massive bottleneck as data scales. Consolidation into a single SQL query using subqueries and aliased JOINs, combined with tailored composite indexes (e.g., `(control_id, assessment_date)`), provides logarithmic performance gains.
**Action:** Always offload filtering and aggregation to the database using `func.max()` and `subquery()` patterns in SQLAlchemy, and ensure indexes cover both the join keys and the sorting/max columns.
