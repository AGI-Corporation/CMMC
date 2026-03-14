## 2026-05-21 - Centralized Query Optimization for Assessments

**Learning:** Duplicated "latest assessment per control" query logic across routers (controls, assessment, reports, orchestrator) leads to maintenance overhead and prevents consistent performance optimizations. Moving this logic to a shared helper in `backend/db/database.py` and adding a composite index `idx_control_date` on `(control_id, assessment_date)` significantly speeds up assessment retrieval, especially when filtered by a subset of controls.

**Action:** Always centralize frequent query patterns that involve grouping or joining on latest records. Use composite indexes to support these queries at the database layer.
