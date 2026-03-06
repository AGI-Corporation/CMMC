
## 2026-03-06 - [SQL Join & Index Optimization]
**Learning:** In-memory joins and Python-level filtering on large datasets (Controls/Assessments) significantly impact performance as the database grows. Replacing dual-query patterns with a single SQLAlchemy `LEFT JOIN` on a "latest-record" subquery reduces DB roundtrips.
**Action:** Always check for N+1 or dual-query patterns when fetching related records with "latest" semantics. Ensure composite indexes like `(foreign_id, date_field)` are in place for subquery performance.
