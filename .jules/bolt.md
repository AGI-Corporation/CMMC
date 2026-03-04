## 2025-03-04 - [Database-Level Filtering for Implementation Status]
**Learning:** In this architecture, 'not_started' status is represented by the absence of an `AssessmentRecord`. Python-side filtering for this status after fetching all controls is an anti-pattern that leads to O(N) database queries or massive over-fetching.
**Action:** Use a `LEFT OUTER JOIN` with a subquery for the latest assessment and explicitly check `AssessmentRecord.id.is_(None)` in the SQL `WHERE` clause to filter for 'not_started' controls at the database level.

## 2025-03-04 - [Optimizing Latest-State Queries]
**Learning:** Fetching the "latest state" for 110+ controls (Standard CMMC L2) is the most frequent and expensive operation. A composite index on `(control_id, assessment_date)` is critical for the performance of the subquery join used to resolve the latest assessment.
**Action:** Always ensure `AssessmentRecord` has a composite index on `control_id` and `assessment_date` when implementing framework-wide status lookups.
