## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching for ORM Performance]
**Learning:** Instantiating full SQLAlchemy ORM objects for thousands of records when only a few fields are needed (e.g., status, id) adds significant overhead (~40% in this app). Returning `Row` objects instead of full models for summary endpoints avoids expensive hydration of large text fields like `description` and `notes`.
**Action:** Use `get_latest_assessments(db, columns=[AssessmentRecord.status])` and `select(ControlRecord.id, ...)` for aggregate/summary views to minimize memory usage and hydration time.
