"""
Shared constants for the CMMC Compliance Platform.
AGI Corporation 2026
"""

# SPRS point deductions per control (DoD assessment methodology, NIST SP 800-171A).
# Total possible score = 110.  Floor is -203.
SPRS_DEDUCTIONS: dict[str, int] = {
    # High-value controls (5 points each)
    "AC.2.006": 5, "AC.2.007": 5, "AC.3.017": 5, "AC.3.018": 5,
    "IA.3.083": 5, "IA.3.084": 5, "SC.3.177": 5,
    # Medium-value controls (3 points each)
    "AC.1.001": 3, "AC.1.002": 3, "IA.1.076": 3, "IA.1.077": 3,
    "SC.1.175": 3, "SC.1.176": 3, "SI.1.210": 3, "SI.1.211": 3,
    "SI.1.212": 3, "SI.1.213": 3,
}
