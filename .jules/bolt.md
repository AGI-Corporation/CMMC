## 2025-05-15 - [Database Indexing & Query Filtering]
**Learning:** Fetching 'latest per group' in SQL can be extremely slow without proper indexing. Combining a composite index (control_id, assessment_date) with application-level filtering (passing specific IDs to the query) provides a massive performance boost (~75% reduction in latency) by allowing the DB to skip scanning irrelevant records.
**Action:** Always check if 'latest per group' queries are using a composite index and if the query set can be narrowed down using IDs from a previous (filtered) result.
