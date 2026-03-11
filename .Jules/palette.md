## 2026-05-22 - [Visual Scannability in Compliance Reports]
**Learning:** For GRC and compliance platforms, raw data in reports (like status strings or float confidence scores) can be overwhelming. Adding visual cues like emojis for status, star ratings for confidence, and progress bars for overall posture significantly improves scannability for human auditors without breaking machine-readability if formatted correctly.
**Action:** Use `get_status_emoji`, `get_confidence_stars`, and `get_progress_bar` patterns for any human-facing Markdown or PDF report generation.
