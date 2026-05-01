## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching for ORM Performance]
**Learning:** For summary endpoints and dashboards, fetching full ORM objects with large `Text` or `JSON` fields (like `notes` or `description`) introduces significant overhead. Selective column fetching (projection) can reduce execution time by 30-50% on datasets with hundreds of controls and thousands of assessments. SQLAlchemy `Row` objects are attribute-accessible and serve as lightweight drop-in replacements for models in these logic loops.
**Action:** Use `select(Model.col1, Model.col2)` and `result.all()` for summary/dashboard logic instead of `select(Model)` and `result.scalars().all()`.
