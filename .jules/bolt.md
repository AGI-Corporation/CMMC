## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching with SQLAlchemy Rows]
**Learning:** Using selective column fetching with SQLAlchemy returns `Row` objects instead of Model instances. These rows support attribute access, making them excellent lightweight drop-in replacements for dashboard and summary logic. However, you MUST ensure all columns used in the logic (including fallbacks/calculations like `score_value`) are explicitly fetched, or you'll hit `AttributeError`.
**Action:** When optimizing summary endpoints, use `select(Model.col1, ...)` but double-check every `getattr` or dot-access in the following loop to ensure the column is included in the projection.
