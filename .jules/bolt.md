## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching for Summary Endpoints]
**Learning:** Fetching full ORM model instances for large tables like `ControlRecord` and `AssessmentRecord` (which contain heavy text fields like `description` and `notes`) adds significant overhead for summary/dashboard endpoints. Selective column fetching using SQLAlchemy `Row` objects can improve performance by ~25-60%.
**Action:** Use the updated `get_latest_assessments(db, columns=[...])` and `select(Model.col1, Model.col2)` for summary endpoints that don't need full object state.
