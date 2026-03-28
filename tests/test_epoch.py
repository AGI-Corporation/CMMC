"""
Comprehensive epoch (time-ordered) tests for the CMMC Compliance Platform.

"Epoch" tests verify that the system correctly handles assessment history:
the latest assessment always supersedes older ones, SPRS scores and dashboard
metrics evolve predictably as controls are assessed and re-assessed over time,
and reports reflect the authoritative (most-recent) state.

Controls seeded by the OSCAL catalog and their SPRS deductions:
    AC.1.001 → 3 pts   AC.1.002 → 3 pts   AC.2.006 → 5 pts   AC.2.007 → 5 pts
    IA.1.076 → 3 pts   IA.3.083 → 5 pts   SC.1.175 → 3 pts   SI.1.210 → 3 pts
    Total = 30 pts  →  Baseline SPRS = 110 - 30 = 80
"""

import pytest
import os
import uuid
from datetime import datetime, timedelta, UTC
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.main import app
from backend.db.database import (
    init_db, engine, Base, AsyncSessionLocal,
    AssessmentRecord, get_latest_assessments,
)

# ─── SPRS reference constants (mirrors assessment.py) ─────────────────────────

SPRS_DEDUCTIONS = {
    "AC.1.001": 3, "AC.1.002": 3, "AC.2.006": 5, "AC.2.007": 5,
    "IA.1.076": 3, "IA.3.083": 5, "SC.1.175": 3, "SI.1.210": 3,
}
ALL_CONTROLS = list(SPRS_DEDUCTIONS.keys())
TOTAL_DEDUCTIONS = sum(SPRS_DEDUCTIONS.values())   # 30
BASELINE_SPRS = 110 - TOTAL_DEDUCTIONS              # 80


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def setup_epoch_db():
    """Drop and re-create the database so epoch tests start from a clean state."""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_epoch.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_epoch.db"):
        os.remove("./test_epoch.db")


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _insert_assessment(
    control_id: str,
    status: str,
    confidence: float,
    *,
    days_ago: float = 0,
    notes: str = "",
    poam_required: str = "false",
) -> str:
    """Insert an AssessmentRecord directly with a controlled timestamp."""
    async with AsyncSessionLocal() as session:
        record = AssessmentRecord(
            id=str(uuid.uuid4()),
            control_id=control_id,
            status=status,
            confidence=confidence,
            notes=notes,
            assessment_date=datetime.now(UTC) - timedelta(days=days_ago),
            poam_required=poam_required,
        )
        session.add(record)
        await session.commit()
        return record.id


async def _patch_control(control_id: str, payload: dict) -> dict:
    """PATCH a control via the API and return the response JSON."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.patch(f"/api/controls/{control_id}", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _get_sprs() -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/sprs")
    assert resp.status_code == 200
    return resp.json()


async def _get_dashboard() -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/assessment/dashboard")
    assert resp.status_code == 200
    return resp.json()


async def _get_control(control_id: str) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/api/controls/{control_id}")
    assert resp.status_code == 200
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 0 — Baseline: fresh database, no assessments
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch0_sprs_baseline():
    """Epoch 0: With no assessments every control counts as not_started.
    SPRS = 110 - total_deductions = 80."""
    data = await _get_sprs()
    assert data["sprs_score"] == BASELINE_SPRS
    assert data["controls_implemented"] == 0
    assert data["controls_not_implemented"] == len(ALL_CONTROLS)
    assert data["max_score"] == 110


@pytest.mark.anyio
async def test_epoch0_dashboard_baseline():
    """Epoch 0: Dashboard reports zero compliance at baseline."""
    data = await _get_dashboard()
    assert data["implemented"] == 0
    assert data["compliance_percentage"] == 0.0
    assert data["total_controls"] == len(ALL_CONTROLS)


@pytest.mark.anyio
async def test_epoch0_controls_all_not_started():
    """Epoch 0: Every control detail shows not_started (no assessments yet)."""
    for ctrl_id in ALL_CONTROLS:
        data = await _get_control(ctrl_id)
        assert data["implementation_status"] == "not_started", (
            f"{ctrl_id} should be not_started at baseline"
        )
        assert data["confidence"] == 0.0


@pytest.mark.anyio
async def test_epoch0_list_controls_not_started_filter():
    """Epoch 0: Filtering controls by status=not_started returns all 8."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/controls/?status=not_started")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(ALL_CONTROLS)


@pytest.mark.anyio
async def test_epoch0_sprs_cert_level_below_threshold():
    """Epoch 0: Baseline SPRS=80 qualifies as Level 1 Eligible (0 ≤ score < 88)."""
    data = await _get_sprs()
    assert data["certification_level"] == "Level 1 Eligible"


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 1 — First implementation: mark AC.1.001 as implemented via API PATCH
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch1_implement_one_control():
    """Epoch 1: Implementing AC.1.001 (3-pt deduction) raises SPRS by 3."""
    before = (await _get_sprs())["sprs_score"]
    await _patch_control("AC.1.001", {
        "implementation_status": "implemented",
        "notes": "Epoch 1 - initial implementation",
        "responsible_party": "SecurityTeam",
        "confidence": 0.9,
    })
    after = (await _get_sprs())["sprs_score"]
    assert after == before + SPRS_DEDUCTIONS["AC.1.001"]   # +3 → 83


@pytest.mark.anyio
async def test_epoch1_control_detail_reflects_patch():
    """Epoch 1: Control detail shows the newly patched values."""
    data = await _get_control("AC.1.001")
    assert data["implementation_status"] == "implemented"
    assert data["confidence"] == 0.9
    assert "Epoch 1" in data["notes"]


@pytest.mark.anyio
async def test_epoch1_dashboard_one_implemented():
    """Epoch 1: Dashboard shows exactly 1 implemented control."""
    data = await _get_dashboard()
    assert data["implemented"] == 1
    assert data["compliance_percentage"] == round(1 / len(ALL_CONTROLS) * 100, 2)


@pytest.mark.anyio
async def test_epoch1_list_filter_implemented():
    """Epoch 1: Filter controls by status=implemented returns only AC.1.001."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/controls/?status=implemented")
    data = resp.json()
    assert data["total"] == 1
    assert data["controls"][0]["control"]["id"] == "AC.1.001"


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 2 — Latest-assessment-wins: multiple records for same control
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch2_older_assessment_does_not_override():
    """Epoch 2: Inserting an older 'partial' record for AC.1.001 must NOT override
    the more recent 'implemented' record created in Epoch 1."""
    # Insert an old partial assessment (10 days in the past → older than epoch 1)
    await _insert_assessment("AC.1.001", "partial", 0.4, days_ago=10, notes="Old stale partial")

    data = await _get_control("AC.1.001")
    # The epoch-1 implemented record (newer) must still win
    assert data["implementation_status"] == "implemented"
    assert data["confidence"] == 0.9


@pytest.mark.anyio
async def test_epoch2_get_latest_assessments_helper_returns_newest():
    """Epoch 2: The get_latest_assessments DB helper returns the most recent record."""
    async with AsyncSessionLocal() as session:
        result = await get_latest_assessments(session, control_ids=["AC.1.001"])
    assert "AC.1.001" in result
    rec = result["AC.1.001"]
    assert rec.status == "implemented"
    assert rec.confidence == 0.9


@pytest.mark.anyio
async def test_epoch2_history_preserved_in_db():
    """Epoch 2: Both old and new assessment records coexist in the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AssessmentRecord).where(AssessmentRecord.control_id == "AC.1.001")
        )
        records = result.scalars().all()
    # At least: 1 from epoch 1 (API patch) + 1 stale inserted above
    assert len(records) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 3 — Status regression: a newer assessment worsens a control's status
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch3_status_regression_via_patch():
    """Epoch 3: Patching AC.1.001 to partially_implemented (newer) regresses status
    and SPRS drops by 3."""
    before = (await _get_sprs())["sprs_score"]
    await _patch_control("AC.1.001", {
        "implementation_status": "partially_implemented",
        "notes": "Epoch 3 - re-assessment revealed gaps",
        "responsible_party": "Auditor",
        "confidence": 0.55,
    })
    after = (await _get_sprs())["sprs_score"]
    assert after == before - SPRS_DEDUCTIONS["AC.1.001"]   # -3


@pytest.mark.anyio
async def test_epoch3_control_shows_regressed_status():
    """Epoch 3: Control detail now shows the regressed status."""
    data = await _get_control("AC.1.001")
    assert data["implementation_status"] == "partially_implemented"
    assert data["confidence"] == 0.55


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 4 — High-value control; certification level threshold
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch4_high_value_control_5pt():
    """Epoch 4: Implementing IA.3.083 (5-pt deduction) raises SPRS by 5."""
    before = (await _get_sprs())["sprs_score"]
    await _patch_control("IA.3.083", {
        "implementation_status": "implemented",
        "notes": "MFA enforced for all privileged users",
        "responsible_party": "IdentityTeam",
        "confidence": 1.0,
    })
    after = (await _get_sprs())["sprs_score"]
    assert after == before + SPRS_DEDUCTIONS["IA.3.083"]   # +5


@pytest.mark.anyio
async def test_epoch4_certification_level_changes():
    """Epoch 4: SPRS score determines the certification level bucket."""
    data = await _get_sprs()
    score = data["sprs_score"]
    cert = data["certification_level"]
    if score >= 88:
        assert cert == "Level 2 Eligible"
    elif score >= 0:
        assert cert == "Level 1 Eligible"
    else:
        assert cert == "Below Threshold - Remediation Required"


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 5 — Multiple controls in same epoch; combined SPRS delta
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch5_multi_control_same_epoch():
    """Epoch 5: Implementing IA.1.076 (3pt) + SC.1.175 (3pt) raises SPRS by 6."""
    before = (await _get_sprs())["sprs_score"]

    await _patch_control("IA.1.076", {
        "implementation_status": "implemented",
        "confidence": 0.88,
        "notes": "Unique IDs enforced",
        "responsible_party": "IAMTeam",
    })
    await _patch_control("SC.1.175", {
        "implementation_status": "implemented",
        "confidence": 0.92,
        "notes": "Boundary protection implemented",
        "responsible_party": "NetworkTeam",
    })

    after = (await _get_sprs())["sprs_score"]
    expected_delta = SPRS_DEDUCTIONS["IA.1.076"] + SPRS_DEDUCTIONS["SC.1.175"]  # 6
    assert after == before + expected_delta


@pytest.mark.anyio
async def test_epoch5_dashboard_reflects_multi_impl():
    """Epoch 5: Dashboard implemented count accounts for all newly implemented controls."""
    data = await _get_dashboard()
    # IA.3.083, IA.1.076, SC.1.175 are implemented; AC.1.001 is partially_implemented
    assert data["implemented"] >= 3


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 6 — Evidence-linked assessment
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch6_evidence_ids_persisted():
    """Epoch 6: Assessment with evidence IDs stores and retrieves them correctly.
    The PATCH endpoint returns confidence/poam_required but evidence_count is
    available via the detail GET endpoint (see test_epoch6_evidence_count_in_detail)."""
    resp = await _patch_control("AC.2.006", {
        "implementation_status": "implemented",
        "notes": "PAM tool deployed",
        "responsible_party": "CloudTeam",
        "evidence_ids": ["ev-scan-001", "ev-policy-002", "ev-config-003"],
        "confidence": 0.95,
        "poam_required": False,
    })
    assert resp["confidence"] == 0.95
    assert resp["poam_required"] is False


@pytest.mark.anyio
async def test_epoch6_evidence_count_in_detail():
    """Epoch 6: Control detail endpoint reflects the evidence count correctly."""
    data = await _get_control("AC.2.006")
    assert data["evidence_count"] == 3
    assert data["implementation_status"] == "implemented"


@pytest.mark.anyio
async def test_epoch6_poam_required_flag():
    """Epoch 6: poam_required=True is stored and surfaced correctly.
    Using status='planned' (a POAM-eligible status reachable via the API)."""
    resp = await _patch_control("AC.2.007", {
        "implementation_status": "planned",
        "notes": "Pending vendor quote",
        "responsible_party": "Procurement",
        "confidence": 0.0,
        "poam_required": True,
    })
    assert resp["poam_required"] is True

    data = await _get_control("AC.2.007")
    assert data["poam_required"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 7 — POAM report accuracy
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch7_poam_excludes_implemented_controls():
    """Epoch 7: POAM CSV omits fully-implemented controls."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/poam")
    assert resp.status_code == 200
    csv_text = resp.text
    assert "Control ID,Domain" in csv_text      # header present
    # IA.3.083 is implemented → must NOT appear in POAM
    assert "IA.3.083" not in csv_text


@pytest.mark.anyio
async def test_epoch7_poam_includes_partial_controls():
    """Epoch 7: POAM CSV includes partially_implemented controls (AC.1.001)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/poam")
    assert resp.status_code == 200
    # AC.1.001 is partially_implemented → must appear
    assert "AC.1.001" in resp.text


@pytest.mark.anyio
async def test_epoch7_poam_includes_not_implemented_controls():
    """Epoch 7: POAM CSV includes planned controls (AC.2.007 was set to planned in epoch 6)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/poam")
    assert resp.status_code == 200
    assert "AC.2.007" in resp.text


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 8 — SSP report reflects latest state
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch8_ssp_structure():
    """Epoch 8: SSP Markdown document has required structural elements."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/ssp")
    assert resp.status_code == 200
    text = resp.text
    assert "# System Security Plan" in text
    assert "Overall Compliance" in text or "Overall Progress" in text
    assert "## 3. Assessment Findings" in text


@pytest.mark.anyio
async def test_epoch8_ssp_contains_implemented_controls():
    """Epoch 8: SSP includes sections for the implemented controls."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/ssp")
    assert resp.status_code == 200
    # At least one implemented control should appear in the findings section
    text = resp.text
    # IA.3.083, IA.1.076, SC.1.175, AC.2.006 are all implemented
    implemented_ids = ["IA.3.083", "IA.1.076", "SC.1.175", "AC.2.006"]
    assert any(ctrl_id in text for ctrl_id in implemented_ids)


@pytest.mark.anyio
async def test_epoch8_ssp_confidence_stars():
    """Epoch 8: SSP renders confidence stars for assessed controls."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/ssp")
    text = resp.text
    # Confidence 1.0 → ⭐⭐⭐⭐⭐; confidence 0.55 → ⭐⭐⭐☆☆ (int(0.55*5+0.5)=3)
    assert "⭐" in text


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 9 — PATCH preserves full history in DB
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch9_patch_appends_not_overwrites():
    """Epoch 9: Each PATCH call inserts a new AssessmentRecord; old records stay."""
    control_id = "SI.1.210"

    # Insert an older partial record directly
    await _insert_assessment(control_id, "partial", 0.4, days_ago=5, notes="Epoch 9 old")

    # Patch via API to implemented (newer timestamp)
    await _patch_control(control_id, {
        "implementation_status": "implemented",
        "notes": "Epoch 9 new",
        "responsible_party": "SysAdmin",
    })

    # Both records should be in the DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AssessmentRecord).where(AssessmentRecord.control_id == control_id)
        )
        records = result.scalars().all()

    assert len(records) >= 2, "Both old and new records must coexist"
    statuses = {r.status for r in records}
    assert "partial" in statuses
    assert "implemented" in statuses


@pytest.mark.anyio
async def test_epoch9_latest_wins_after_history_accumulates():
    """Epoch 9: After accumulating history, get_latest_assessments still returns newest."""
    async with AsyncSessionLocal() as session:
        result = await get_latest_assessments(session, control_ids=["SI.1.210"])
    assert result["SI.1.210"].status == "implemented"


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 10 — Control list filtering uses latest assessment
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch10_filter_implemented_only_latest():
    """Epoch 10: Status filter on list endpoint uses only the latest assessment."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/controls/?status=implemented")
    assert resp.status_code == 200
    data = resp.json()
    for c in data["controls"]:
        assert c["implementation_status"] == "implemented", (
            f"Control {c['control']['id']} should be implemented but got "
            f"{c['implementation_status']}"
        )


@pytest.mark.anyio
async def test_epoch10_filter_partially_implemented():
    """Epoch 10: AC.1.001 (partial from epoch 3) appears under partially_implemented filter."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/controls/?status=partially_implemented")
    assert resp.status_code == 200
    data = resp.json()
    ids = [c["control"]["id"] for c in data["controls"]]
    assert "AC.1.001" in ids


@pytest.mark.anyio
async def test_epoch10_filter_by_domain():
    """Epoch 10: Domain filter returns only controls from that domain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/controls/?domain=IA")
    assert resp.status_code == 200
    data = resp.json()
    for c in data["controls"]:
        assert c["control"]["domain"] == "IA"


# ═══════════════════════════════════════════════════════════════════════════════
# EPOCH 11 — SPRS score bounds and full compliance
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_epoch11_sprs_score_within_bounds():
    """Epoch 11: SPRS score is always within the -203 to 110 range."""
    data = await _get_sprs()
    assert -203 <= data["sprs_score"] <= 110


@pytest.mark.anyio
async def test_epoch11_full_compliance_sprs_110():
    """Epoch 11: When all controls are implemented SPRS score reaches 110."""
    # Remaining non-implemented controls:
    #   AC.1.001 (partially_implemented from epoch 3, 3pts)
    #   AC.1.002 (never implemented, 3pts)
    #   AC.2.007 (planned from epoch 6, 5pts)
    remaining = ["AC.1.001", "AC.1.002", "AC.2.007"]
    for ctrl_id in remaining:
        await _patch_control(ctrl_id, {
            "implementation_status": "implemented",
            "notes": f"Epoch 11 - full compliance sweep for {ctrl_id}",
            "responsible_party": "CISOOffice",
            "confidence": 1.0,
        })

    data = await _get_sprs()
    assert data["sprs_score"] == 110
    assert data["controls_implemented"] == len(ALL_CONTROLS)
    assert data["controls_not_implemented"] == 0


@pytest.mark.anyio
async def test_epoch11_full_compliance_cert_level():
    """Epoch 11: At SPRS=110 the certification level is Level 2 Eligible."""
    data = await _get_sprs()
    assert data["sprs_score"] == 110
    assert data["certification_level"] == "Level 2 Eligible"


@pytest.mark.anyio
async def test_epoch11_full_compliance_dashboard():
    """Epoch 11: Dashboard shows 100% compliance and all controls implemented."""
    data = await _get_dashboard()
    assert data["implemented"] == len(ALL_CONTROLS)
    assert data["compliance_percentage"] == 100.0
    assert data["not_implemented"] == 0


@pytest.mark.anyio
async def test_epoch11_full_compliance_poam_empty():
    """Epoch 11: At full compliance the POAM contains no data rows."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/poam")
    assert resp.status_code == 200
    lines = [ln for ln in resp.text.strip().splitlines() if ln.strip()]
    # Only the CSV header row, no data rows
    assert len(lines) == 1
    assert "Control ID" in lines[0]
