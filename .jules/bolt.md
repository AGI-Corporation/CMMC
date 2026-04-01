## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-21 - [Selective Column Fetching for Summaries]
**Learning:** Fetching full ORM objects (including large Text and JSON columns) for summary calculations (like dashboards or score deductions) is a major overhead. Selective column fetching using `select(*columns)` with SQLAlchemy's `all()` returns Row objects that are attribute-accessible and significantly faster.
**Action:** Use selective column fetching for any endpoint that only requires a subset of fields, especially when those fields are part of records with large blobs.
