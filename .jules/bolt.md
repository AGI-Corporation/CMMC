## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching with SQLAlchemy Rows]
**Learning:** Instantiating full SQLAlchemy ORM models with large Text/JSON fields (like `description` and `notes`) for summary dashboards is a major bottleneck. Using `select(columns)` with `result.all()` returns `Row` objects that support attribute access (`row.field`), allowing them to be drop-in replacements for models in many cases while avoiding ORM overhead.
**Action:** Use the updated `get_latest_assessments(db, columns=[...])` helper for summary/dashboard endpoints to achieve ~40-50% speedups on large datasets.
