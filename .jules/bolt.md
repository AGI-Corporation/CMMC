## 2026-05-20 - [Optimizing Latest Per Group Query Pattern]
**Learning:** The 'latest per control' pattern is a major bottleneck when the assessment table grows. A composite index on `(control_id, assessment_date)` combined with a consolidated helper that supports ID-based filtering significantly reduces retrieval time.
**Action:** Always use `get_latest_assessments(db, control_ids=filtered_ids)` instead of fetching all assessments and filtering in Python or using un-indexed subqueries.

## 2026-05-21 - [Selective Column Fetching Pitfalls]
**Learning:** Selective column fetching (`select(Model.col1, Model.col2)`) significantly reduces ORM overhead and database payload, but it returns SQLAlchemy `Row` objects instead of full Model instances. This can break code that expects Model behaviors or fields that were inadvertently omitted (e.g., `score_value` for SPRS logic or `description` for reports).
**Action:** When using selective fetching, explicitly audit all fields used in the downstream logic and ensure `get_latest_assessments` handles the transition from Model to Row objects gracefully to avoid type-mismatch "foot-guns".
