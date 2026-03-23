## 2026-03-05 - [Composite Index for Latest-Per-Group]
**Learning:** In SQLite, a composite index on `(control_id, assessment_date)` significantly speeds up "latest per group" queries when combined with an `IN` clause filter on `control_id`, reducing latency from ~0.050s to ~0.012s (~75% improvement) for partial views (e.g., domain-filtered control lists).
**Action:** Always pair "latest per group" subqueries with targeted ID filtering and composite indexes on the group-by and order-by columns.
