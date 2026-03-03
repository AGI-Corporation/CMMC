## 2025-05-15 - [Database Indexing for Latest Record Retrieval]
**Learning:** In a history-tracking system like compliance assessments, the most frequent query is fetching the *latest* state for each entity. Without a composite index on (foreign_key, timestamp), this becomes an O(N) scan that degrades linearly as history grows.
**Action:** Always implement a composite index on (entity_id, created_at/date) when using subquery joins or window functions for "top-1 per group" queries.

## 2025-05-15 - [Centralizing Core Query Logic]
**Learning:** Redundant implementations of complex SQL queries (like latest record retrieval) across multiple routers leads to maintenance debt and inconsistent performance optimizations.
**Action:** Centralize core database access patterns into the `db/` layer or a dedicated service layer, providing flexible return types (e.g., `as_dict`) to accommodate different consumer needs.
