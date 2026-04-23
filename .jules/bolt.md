## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Optimizing Summary Endpoints with Selective Column Fetching]
**Learning:** Loading full ORM objects with large Text fields (like `ControlRecord.description` or `AssessmentRecord.notes`) incurs significant overhead in database I/O and object instantiation, even when only a few status/score fields are needed for calculations.
**Action:** Use selective column fetching (via SQLAlchemy `select(Model.col1, Model.col2)`) in summary/dashboard endpoints to minimize data transfer and memory usage.
