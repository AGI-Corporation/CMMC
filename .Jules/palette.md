## 2026-03-08 - Separation of Data and Presentation

**Learning:** Presentation logic, such as adding emojis or visual formatting, should be strictly separated from data contracts in the backend. Injecting visual indicators into API return values can break frontend conditional logic and makes the system less maintainable.

**Action:** Keep API responses clean and focused on raw data. Apply visual enhancements (emojis, progress bars) only in human-readable exports (like Markdown/PDF) or in the frontend UI layer.
