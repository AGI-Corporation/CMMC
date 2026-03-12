## 2025-05-15 - [Database Indexing for Latest Per Group]
**Learning:** The application frequently queries the "latest assessment for each control". Without an index, this involves a full scan of the `assessments` table for the subquery and the join. A composite index on `(control_id, assessment_date)` significantly speeds up this specific `GROUP BY` and `JOIN` pattern.
**Action:** Always check for "latest record per group" query patterns and ensure a composite index exists on the grouping column and the sort column.
