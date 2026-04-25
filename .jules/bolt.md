## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching with Row Objects]
**Learning:** Fetching full SQLAlchemy model instances for summary endpoints (Dashboard, SPRS) introduces significant ORM overhead, especially when tables contain large text fields. Using selective column fetching with  returns lightweight  objects which are much faster to instantiate and still support attribute-style access.
**Action:** Use the  parameter in  and selective  for summary/list endpoints to avoid loading unneeded large fields like `description` or `notes`.

## 2026-05-20 - [Selective Column Fetching with Row Objects]
**Learning:** Fetching full SQLAlchemy model instances for summary endpoints (Dashboard, SPRS) introduces significant ORM overhead, especially when tables contain large text fields. Using selective column fetching with `select(*columns)` returns lightweight `Row` objects which are much faster to instantiate and still support attribute-style access.
**Action:** Use the `columns` parameter in `get_latest_assessments` and selective `select()` for summary/list endpoints to avoid loading unneeded large fields like `description` or `notes`.
