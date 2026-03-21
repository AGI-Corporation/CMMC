## 2026-05-22 - [Visual SSP Enhancements]
**Learning:** Presentation enhancements (emojis, progress bars, and star ratings) significantly improve the scannability of human-readable reports (like Markdown or PDF) without altering the underlying data structure. Using standard Unicode characters like `█` and `░` ensures cross-platform compatibility for visual progress bars in text-based formats.
**Action:** Always separate presentation logic (emojis, formatting) from raw data fields in API responses to ensure machine-readability is preserved while enhancing human-readable outputs.
