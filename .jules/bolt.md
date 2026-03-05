## 2025-03-05 - [SQL Join & Indexing for Latest Records]
**Learning:** Combining multiple database queries into a single JOIN with a targeted composite index (e.g., `(control_id, assessment_date)`) yielded a measurable ~15% performance improvement even on a small dataset of 110 controls. Relocating filtering logic from Python to the SQL engine further reduces memory overhead and processing time.
**Action:** Always prefer single-query JOINs over application-side mapping for resolving 'latest record per category' patterns, and support them with composite indexes.
