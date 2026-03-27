"""
Extended Controls, Assessment, and Reports Tests
Covers: control filtering, 404 paths, domain endpoint, assessment dashboard,
promote edge cases, SPRS score structure, SSP/POAM custom parameters,
root endpoint health.
"""
import pytest
import os
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_controls_ext.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_controls_ext.db"):
        os.remove("./test_controls_ext.db")


# ── Health / root ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_root_endpoint():
    """Root endpoint returns service information and healthy status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "mcp_endpoint" in data
    assert "docs" in data


# ── Controls filtering ────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_controls_filter_by_level_1():
    """Filter controls to Level 1 only."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/", params={"level": "Level 1"})
    assert response.status_code == 200
    data = response.json()
    assert data["level_filter"] == "Level 1"
    assert data["total"] > 0
    for item in data["controls"]:
        assert item["control"]["level"] == "Level 1"


@pytest.mark.anyio
async def test_list_controls_filter_by_level_2():
    """Filter controls to Level 2 only."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/", params={"level": "Level 2"})
    assert response.status_code == 200
    data = response.json()
    assert data["level_filter"] == "Level 2"
    for item in data["controls"]:
        assert item["control"]["level"] == "Level 2"


@pytest.mark.anyio
async def test_list_controls_filter_by_domain_ac():
    """Filter controls to AC domain only."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/", params={"domain": "AC"})
    assert response.status_code == 200
    data = response.json()
    assert data["domain_filter"] == "AC"
    assert data["total"] > 0
    for item in data["controls"]:
        assert item["control"]["domain"] == "AC"


@pytest.mark.anyio
async def test_list_controls_filter_by_domain_ia():
    """Filter controls to IA domain only."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/", params={"domain": "IA"})
    assert response.status_code == 200
    data = response.json()
    assert data["domain_filter"] == "IA"
    for item in data["controls"]:
        assert item["control"]["domain"] == "IA"


@pytest.mark.anyio
async def test_list_controls_filter_by_status_not_started():
    """All unassessed controls have not_started status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/", params={"status": "not_started"})
    assert response.status_code == 200
    data = response.json()
    for item in data["controls"]:
        assert item["implementation_status"] == "not_started"


@pytest.mark.anyio
async def test_list_controls_filter_by_status_implemented():
    """Implement a control then filter by implemented status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.patch("/api/controls/AC.1.001", json={
            "implementation_status": "implemented",
            "notes": "Fully implemented",
            "responsible_party": "Security Team",
        })
        response = await ac.get("/api/controls/", params={"status": "implemented"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["controls"]:
        assert item["implementation_status"] == "implemented"


@pytest.mark.anyio
async def test_list_controls_combined_level_domain_filter():
    """Combine level and domain filters."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/", params={"level": "Level 1", "domain": "AC"})
    assert response.status_code == 200
    data = response.json()
    for item in data["controls"]:
        assert item["control"]["level"] == "Level 1"
        assert item["control"]["domain"] == "AC"


# ── Control detail / 404 ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_control_not_found():
    """Requesting a non-existent control ID returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/XX.9.999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_update_control_not_found():
    """Patching a non-existent control returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch("/api/controls/XX.9.999", json={
            "implementation_status": "implemented",
            "notes": "N/A",
            "responsible_party": "Tester",
        })
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_control_all_statuses():
    """Each valid ImplementationStatus value is accepted by the PATCH endpoint."""
    statuses = [
        "not_started", "in_progress", "implemented",
        "not_applicable", "partially_implemented", "planned",
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for status in statuses:
            response = await ac.patch("/api/controls/AC.1.002", json={
                "implementation_status": status,
                "notes": f"Status: {status}",
                "responsible_party": "Test Team",
            })
            assert response.status_code == 200, f"Failed for status '{status}'"


# ── Domain endpoint ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_controls_by_domain_ia():
    """Domain sub-route returns controls for the given domain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/domain/IA")
    assert response.status_code == 200
    data = response.json()
    assert "controls" in data
    assert data["total"] > 0
    for item in data["controls"]:
        assert item["control"]["domain"] == "IA"


@pytest.mark.anyio
async def test_get_controls_by_domain_sc():
    """Domain sub-route works for SC domain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/controls/domain/SC")
    assert response.status_code == 200
    data = response.json()
    for item in data["controls"]:
        assert item["control"]["domain"] == "SC"


# ── Assessment dashboard ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_assessment_dashboard_structure():
    """Assessment dashboard returns expected fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/assessment/dashboard")
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "total_controls", "implemented", "not_implemented",
        "partially_implemented", "not_started", "not_applicable",
        "compliance_percentage", "sprs_score", "by_domain", "by_level", "readiness",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.anyio
async def test_assessment_dashboard_readiness_is_valid():
    """Readiness classification is one of the four defined strings."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/assessment/dashboard")
    data = response.json()
    valid = [
        "Ready for Certification",
        "Near Compliant - Minor Gaps",
        "In Progress - Significant Gaps",
        "Early Stage - Major Remediation Needed",
    ]
    assert data["readiness"] in valid


@pytest.mark.anyio
async def test_assessment_dashboard_sprs_in_range():
    """SPRS score in the dashboard is within the valid range."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/assessment/dashboard")
    data = response.json()
    assert -203 <= data["sprs_score"] <= 110  # DoD SPRS: floor is -203 (max deductions), ceiling is 110


@pytest.mark.anyio
async def test_assessment_dashboard_by_level_keys():
    """by_level contains entries for all three CMMC levels."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/assessment/dashboard")
    data = response.json()
    assert "Level 1" in data["by_level"]
    assert "Level 2" in data["by_level"]
    assert "Level 3" in data["by_level"]


# ── SPRS score ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_sprs_score_structure():
    """SPRS endpoint returns all required fields with valid values."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/assessment/sprs")
    assert response.status_code == 200
    data = response.json()
    required = [
        "sprs_score", "max_score", "controls_assessed",
        "controls_implemented", "controls_not_implemented",
        "deductions", "certification_level", "assessment_date",
    ]
    for field in required:
        assert field in data, f"Missing field: {field}"
    assert data["max_score"] == 110
    assert -203 <= data["sprs_score"] <= 110  # DoD SPRS: floor is -203 (max deductions), ceiling is 110
    assert data["certification_level"] in [
        "Level 2 Eligible",
        "Level 1 Eligible",
        "Below Threshold - Remediation Required",
    ]


@pytest.mark.anyio
async def test_sprs_deductions_list():
    """Each deduction entry has control_id and deduction keys."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/assessment/sprs")
    for deduction in response.json()["deductions"]:
        assert "control_id" in deduction
        assert "deduction" in deduction
        assert deduction["deduction"] >= 1


# ── Promote endpoint ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_promote_not_found():
    """Promoting a non-existent agent run returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/assessment/promote/non-existent-run-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_promote_devsecops_run():
    """Promoting a DevSecOps run creates assessment records."""
    from backend.db.database import AgentRunRecord, AsyncSessionLocal
    from sqlalchemy import select

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assess_resp = await ac.get("/api/agents/devsecops/assess/promote-test-svc")
        assert assess_resp.status_code == 200

        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(AgentRunRecord)
                .where(AgentRunRecord.agent_type == "devsecops")
                .order_by(AgentRunRecord.created_at.desc())
            )
            run = res.scalars().first()
            run_id = run.id

        promote_resp = await ac.post(f"/api/assessment/promote/{run_id}")
    assert promote_resp.status_code == 200
    data = promote_resp.json()
    assert data["status"] == "promoted"
    assert data["run_id"] == run_id
    assert data["assessments_created"] > 0


# ── SSP / POAM parameters ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_ssp_custom_system_name():
    """SSP report includes the custom system_name."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/reports/ssp", params={"system_name": "MyTestSystem"})
    assert response.status_code == 200
    assert "MyTestSystem" in response.text


@pytest.mark.anyio
async def test_ssp_custom_classification():
    """SSP report includes the custom classification."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/reports/ssp",
            params={"system_name": "TestSys", "classification": "TOP SECRET"},
        )
    assert response.status_code == 200
    assert "TOP SECRET" in response.text


@pytest.mark.anyio
async def test_poam_custom_system_name():
    """POAM CSV is generated with a custom system_name in the filename header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/reports/poam", params={"system_name": "MyPOAMSystem"})
    assert response.status_code == 200
    assert "Control ID,Domain" in response.text
    assert "MyPOAMSystem" in response.headers.get("content-disposition", "")


@pytest.mark.anyio
async def test_poam_includes_partial_controls():
    """After marking a control as partially_implemented, it appears in POAM."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.patch("/api/controls/IA.1.076", json={
            "implementation_status": "partially_implemented",
            "notes": "Partially done",
            "responsible_party": "ISSO",
        })
        response = await ac.get("/api/reports/poam")
    assert response.status_code == 200
    assert "IA.1.076" in response.text
