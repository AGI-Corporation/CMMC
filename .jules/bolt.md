## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-21 - [Selective Column Fetching for ORM Performance]
**Learning:** Hydrating full SQLAlchemy ORM models is expensive, especially for tables with large `Text` or `JSON` fields like `AssessmentRecord.notes` or `ControlRecord.description`. Selective column fetching using `select(Model.col1, Model.col2)` and updating helper functions to support a `columns` parameter can reduce execution time by 40-60% for summary endpoints.
**Action:** For dashboard, SPRS, and reporting summary endpoints, only fetch the specific columns required for calculations and display.
