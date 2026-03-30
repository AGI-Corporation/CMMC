## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-03-30 - [Selective Column Fetching for Dashboard Aggregations]
**Learning:** Fetching full ORM objects (like `ControlRecord`) when only a few columns (`id`, `domain`, `level`) are needed for aggregation/scoring is a major overhead. For 110 controls with large description fields, selective fetching is ~57% faster.
**Action:** Use `select(Model.col1, Model.col2)` instead of `select(Model)` in high-traffic aggregation endpoints.
