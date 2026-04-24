# Palette UX Journal - CMMC Compliance Platform

This journal tracks critical UX and accessibility learnings for the CMMC Compliance Platform.

## 2026-03-26 - Visual scannability for Markdown reports
**Learning:** In a backend-heavy system where the primary interface for human stakeholders is a generated Markdown report, visual scannability is paramount. Adding status emojis and progress bars significantly improves the "at-a-glance" understanding of compliance posture.
**Action:** Always include visual progress indicators and status emojis in human-readable reports (Markdown/PDF/CSV).

## 2026-03-27 - Visual Scannability in Markdown Reports
**Learning:** Dense text reports like the System Security Plan (SSP) are difficult to scan for high-level status. Using familiar visual metaphors like emojis (✅/🟡/🛑), star ratings (⭐⭐⭐), and block-based progress bars (█░) significantly improves information density and "at-a-glance" comprehension in non-interactive formats like Markdown.
**Action:** Always consider adding visual markers (emojis, progress bars) to text-based reports to highlight critical status and progress metrics.

## 2026-04-24 - Single source of truth for cross-interface metrics
**Learning:** When metrics (like Zero Trust maturity) are displayed across different interfaces (e.g., Markdown reports and JSON APIs), centralizing the calculation logic and domain mappings is critical for maintaining "UX Trust." Discrepancies between reports and dashboards can lead to user confusion and loss of confidence in the platform's accuracy.
**Action:** Always store shared metric definitions and calculation helpers in a central location (e.g., a constants file or a shared router module) to ensure data consistency across all user-facing endpoints.
