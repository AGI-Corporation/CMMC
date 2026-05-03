## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching for ORM Performance]
**Learning:** Selective column fetching (projections) provides a ~40% performance boost for summary endpoints by avoiding the overhead of instantiating full ORM models, especially for tables with large Text/JSON fields. SQLAlchemy 2.0 `Row` objects are compatible with attribute access, making them good drop-in replacements.
**Action:** Use `.select(Model.col1, Model.col2)` for summary/dashboard endpoints. Ensure all columns needed for logic (e.g., `score_value`) and Pydantic serialization (e.g., `assessment_date`) are included in the projection.
