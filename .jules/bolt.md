## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-21 - [Partial Column Selection for High-Volume Records]
**Learning:** Fetching full SQLAlchemy models (e.g., AssessmentRecord) triggers retrieval of all columns, including large TEXT fields like 'notes'. This causes significant overhead (measured ~37% latency) in aggregate queries like SPRS or ZT scorecards.
**Action:** Use the 'columns' argument in `get_latest_assessments` to select only necessary fields (id, status, confidence) for aggregate calculations.
