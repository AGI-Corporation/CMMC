## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-21 - [Selective Column Fetching for Summary Endpoints]
**Learning:** Fetching full ORM objects with large text fields (like `description` and `notes`) significantly slows down summary endpoints that only need a few fields for calculations. Selective column fetching using `select(Model.col1, Model.col2)` combined with a flexible database helper provides a major performance boost.
**Action:** Use selective column fetching in all summary/dashboard endpoints. Update shared helpers to support an optional `columns` parameter to avoid over-fetching.
