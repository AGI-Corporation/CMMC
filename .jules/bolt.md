## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching with SQLAlchemy]
**Learning:** Switching from full ORM model fetching () to selective column fetching () yields significant performance gains (~30-45%) in summary endpoints by avoiding the overhead of instantiating large objects for every row. However, it requires a "whitelist" approach to ensure all columns required by business logic (like `score_value` for SPRS) or response schemas are included.
**Action:** Use selective fetching for dashboard and report summary logic, but always verify the full dependency graph of columns before trimming the selection.

## 2026-05-20 - [Selective Column Fetching with SQLAlchemy]
**Learning:** Switching from full ORM model fetching (`select(Model)`) to selective column fetching (`select(Model.col1, Model.col2)`) yields significant performance gains (~30-45%) in summary endpoints by avoiding the overhead of instantiating large objects for every row. However, it requires a "whitelist" approach to ensure all columns required by business logic (like `score_value` for SPRS) or response schemas are included.
**Action:** Use selective fetching for dashboard and report summary logic, but always verify the full dependency graph of columns before trimming the selection.
