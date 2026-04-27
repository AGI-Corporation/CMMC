## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-20 - [Selective Column Fetching for Summary Views]
**Learning:** Fetching full ORM model instances for summary endpoints (Dashboard, SPRS, POAM) is expensive due to large `Text` (notes/descriptions) and `JSON` fields. SQL projection using selective column fetching reduces database payload and memory overhead significantly. SQLAlchemy 2.0 `Row` objects serve as efficient drop-in replacements for models when model methods/relationships aren't needed.
**Action:** Use the `columns` parameter in `get_latest_assessments` and explicit `select(Table.col)` for all summary-only queries to bypass loading heavy fields.
