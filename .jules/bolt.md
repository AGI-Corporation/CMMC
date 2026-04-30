## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching for Summary Endpoints]
**Learning:** Fetching full ORM model instances (e.g., `ControlRecord`, `AssessmentRecord`) for summary/dashboard endpoints is a major bottleneck due to overhead from large text fields (`description`, `notes`) and ORM instantiation. SQLAlchemy `Row` objects with selective column fetching provide a significant speed boost (~5-8x) while maintaining attribute-access compatibility.
**Action:** Use selective column fetching (e.g., `select(Model.id, Model.status)`) and the `columns` parameter in `get_latest_assessments` for all endpoints that don't require the full object state.
