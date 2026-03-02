## 2026-05-22 - [SQLAlchemy Optimization: Latest-per-group query]
**Learning:** Composite indexes on `(group_id, timestamp)` significantly speed up "latest record per group" queries by allowing the database to efficiently find the max timestamp within each group using the index.
**Action:** Always use composite indexes when implementing "latest-per-group" patterns in SQLAlchemy/SQL.
