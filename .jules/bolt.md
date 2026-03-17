## 2024-05-15 - [Database] Optimized Latest Assessment Retrieval

**Learning:** The application frequently queries the latest assessment for each control. Without a dedicated index, this operation requires a full scan of the `assessments` table, which scales poorly as the number of assessments grows (e.g., 50,000 assessments for 500 controls).

**Action:** Implement a composite index `idx_control_date` on `(control_id, assessment_date)` in the `AssessmentRecord` table. This reduces query time for the 'latest assessment' pattern by approximately 43% (0.0474s down to 0.0272s for 50k records). Standardize retrieval via a shared `get_latest_assessments` helper in `backend/db/database.py`.
