## 2025-05-20 - Visual Cues in Markdown Reports
**Learning:** Purely text-based compliance reports (SSP/POAM) are difficult to scan quickly. Adding simple visual indicators like emojis (✅/🛑), star-based confidence meters (⭐⭐⭐), and Markdown-compatible progress bars (█░) significantly improves scannability without breaking PDF/print compatibility.
**Action:** Use `get_status_emoji`, `get_confidence_stars`, and `get_progress_bar` helpers for any human-facing Markdown or terminal output to ensure consistent visual language across the platform.
