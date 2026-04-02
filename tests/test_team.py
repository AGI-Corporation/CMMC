"""
Tests for the Enterprise Team Tracking Dashboard
AGI Corporation 2026
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_team_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield


@pytest.mark.anyio
async def test_create_team_member():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/team/members",
            json={
                "name": "Alice Smith",
                "email": "alice@agi.example",
                "role": "ISSO",
                "department": "Security",
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alice Smith"
    assert data["email"] == "alice@agi.example"
    assert data["role"] == "ISSO"
    assert data["active"] is True


@pytest.mark.anyio
async def test_create_duplicate_email_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First creation
        await ac.post(
            "/api/team/members",
            json={"name": "Bob Dup", "email": "dup@agi.example", "role": "Manager"},
        )
        # Second with same email
        resp = await ac.post(
            "/api/team/members",
            json={"name": "Bob Dup2", "email": "dup@agi.example", "role": "Manager"},
        )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_invalid_role_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/team/members",
            json={"name": "Bad Role", "email": "bad@agi.example", "role": "CEO"},
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_team_members():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/team/members")
    assert resp.status_code == 200
    data = resp.json()
    assert "members" in data
    assert data["total"] >= 1
    member = data["members"][0]
    assert "stats" in member
    assert "total_assigned" in member["stats"]


@pytest.mark.anyio
async def test_get_member_detail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Get member id from list
        list_resp = await ac.get("/api/team/members")
        member_id = list_resp.json()["members"][0]["id"]

        resp = await ac.get(f"/api/team/members/{member_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == member_id
    assert "assignments" in data
    assert "stats" in data


@pytest.mark.anyio
async def test_get_nonexistent_member_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/team/members/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_team_member():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_resp = await ac.get("/api/team/members")
        member_id = list_resp.json()["members"][0]["id"]

        resp = await ac.patch(
            f"/api/team/members/{member_id}",
            json={"department": "Cyber Operations", "notes": "Updated"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["department"] == "Cyber Operations"
    assert data["notes"] == "Updated"


@pytest.mark.anyio
async def test_create_assignment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_resp = await ac.get("/api/team/members")
        member_id = list_resp.json()["members"][0]["id"]

        resp = await ac.post(
            "/api/team/assignments",
            json={
                "member_id": member_id,
                "control_id": "AC.1.001",
                "role": "owner",
                "priority": "high",
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["member_id"] == member_id
    assert data["control_id"] == "AC.1.001"
    assert data["role"] == "owner"
    assert data["status"] == "open"
    assert "compliance_status" in data
    assert "control_title" in data


@pytest.mark.anyio
async def test_assignment_invalid_control_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_resp = await ac.get("/api/team/members")
        member_id = list_resp.json()["members"][0]["id"]

        resp = await ac.post(
            "/api/team/assignments",
            json={"member_id": member_id, "control_id": "FAKE.9.999", "role": "owner"},
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_assignment_invalid_member_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/team/assignments",
            json={"member_id": "no-such-member", "control_id": "AC.1.001", "role": "owner"},
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_assignment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Get existing assignment id
        list_resp = await ac.get("/api/team/members")
        member_id = list_resp.json()["members"][0]["id"]
        detail = await ac.get(f"/api/team/members/{member_id}")
        assignment_id = detail.json()["assignments"][0]["id"]

        resp = await ac.patch(
            f"/api/team/assignments/{assignment_id}",
            json={"status": "in_progress", "priority": "critical", "notes": "Working on it"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_progress"
    assert data["priority"] == "critical"


@pytest.mark.anyio
async def test_team_dashboard():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/team/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "org_summary" in data
    assert "domain_summary" in data
    assert "member_posture" in data
    assert "overdue_assignments" in data
    assert "unowned_controls" in data
    assert "team_size" in data

    org = data["org_summary"]
    assert "total_controls" in org
    assert "compliance_pct" in org
    assert "sprs_score" in org
    assert "readiness" in org
    assert "unassigned_controls" in org


@pytest.mark.anyio
async def test_team_dashboard_domain_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/team/dashboard")
    data = resp.json()
    domains = data["domain_summary"]
    assert len(domains) > 0
    for d in domains:
        assert "domain" in d
        assert "total" in d
        assert "compliance_pct" in d
        assert "owners" in d


@pytest.mark.anyio
async def test_overdue_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/team/overdue")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_overdue" in data
    assert "overdue_assignments" in data


@pytest.mark.anyio
async def test_responsibility_matrix():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/team/matrix")
    assert resp.status_code == 200
    data = resp.json()
    assert "members" in data
    assert "controls" in data
    assert "total_controls" in data
    assert "total_members" in data
    # Each control row should have an assignments dict
    if data["controls"]:
        row = data["controls"][0]
        assert "control_id" in row
        assert "domain" in row
        assert "compliance_status" in row
        assert "assignments" in row


@pytest.mark.anyio
async def test_deactivate_member():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a member to deactivate
        create_resp = await ac.post(
            "/api/team/members",
            json={"name": "Temp User", "email": "temp@agi.example", "role": "Other"},
        )
        member_id = create_resp.json()["id"]

        # Deactivate
        del_resp = await ac.delete(f"/api/team/members/{member_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deactivated"

        # Should not appear in active list
        list_resp = await ac.get("/api/team/members?active_only=true")
        ids = [m["id"] for m in list_resp.json()["members"]]
        assert member_id not in ids

        # Should appear in full list
        list_resp_all = await ac.get("/api/team/members?active_only=false")
        ids_all = [m["id"] for m in list_resp_all.json()["members"]]
        assert member_id in ids_all


@pytest.mark.anyio
async def test_delete_assignment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_resp = await ac.get("/api/team/members")
        member_id = list_resp.json()["members"][0]["id"]

        # Create an assignment to delete
        create_resp = await ac.post(
            "/api/team/assignments",
            json={"member_id": member_id, "control_id": "AC.1.002", "role": "reviewer"},
        )
        assignment_id = create_resp.json()["id"]

        # Delete it
        del_resp = await ac.delete(f"/api/team/assignments/{assignment_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"


# ---------------------------------------------------------------------------
# Tests for new endpoints: bulk assignment, domain assignment, workload
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_bulk_assignment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a fresh member for this test
        member_resp = await ac.post(
            "/api/team/members",
            json={"name": "Bulk User", "email": "bulk@agi.example", "role": "Control Owner"},
        )
        member_id = member_resp.json()["id"]

        resp = await ac.post(
            "/api/team/assignments/bulk",
            json={
                "member_id": member_id,
                "control_ids": ["AC.1.001", "AC.1.002", "IA.1.076"],
                "role": "owner",
                "priority": "high",
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 3
    assert data["skipped_already_assigned"] == 0
    assert data["invalid_control_ids"] == []
    assert set(data["created_control_ids"]) == {"AC.1.001", "AC.1.002", "IA.1.076"}


@pytest.mark.anyio
async def test_bulk_assignment_skips_duplicates():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        member_resp = await ac.post(
            "/api/team/members",
            json={"name": "Bulk Dup", "email": "bulkdup@agi.example", "role": "Control Owner"},
        )
        member_id = member_resp.json()["id"]

        # First bulk assign
        await ac.post(
            "/api/team/assignments/bulk",
            json={"member_id": member_id, "control_ids": ["AC.1.001", "AC.1.002"], "role": "owner"},
        )

        # Second bulk assign with same controls — should skip
        resp = await ac.post(
            "/api/team/assignments/bulk",
            json={"member_id": member_id, "control_ids": ["AC.1.001", "AC.1.002"], "role": "owner"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 0
    assert data["skipped_already_assigned"] == 2


@pytest.mark.anyio
async def test_bulk_assignment_invalid_controls():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        member_resp = await ac.post(
            "/api/team/members",
            json={"name": "Bulk Bad", "email": "bulkbad@agi.example", "role": "Control Owner"},
        )
        member_id = member_resp.json()["id"]

        resp = await ac.post(
            "/api/team/assignments/bulk",
            json={
                "member_id": member_id,
                "control_ids": ["AC.1.001", "FAKE.9.999"],
                "role": "owner",
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 1
    assert "FAKE.9.999" in data["invalid_control_ids"]


@pytest.mark.anyio
async def test_bulk_assignment_missing_member():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/team/assignments/bulk",
            json={"member_id": "no-such-member", "control_ids": ["AC.1.001"], "role": "owner"},
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_bulk_assignment_empty_list_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        member_resp = await ac.post(
            "/api/team/members",
            json={"name": "Bulk Empty", "email": "bulkempty@agi.example", "role": "Other"},
        )
        member_id = member_resp.json()["id"]

        resp = await ac.post(
            "/api/team/assignments/bulk",
            json={"member_id": member_id, "control_ids": [], "role": "owner"},
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_domain_assignment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        member_resp = await ac.post(
            "/api/team/members",
            json={"name": "Domain Owner", "email": "domain@agi.example", "role": "ISSO"},
        )
        member_id = member_resp.json()["id"]

        resp = await ac.post(
            f"/api/team/assignments/domain/AC",
            params={"member_id": member_id, "role": "owner", "priority": "high"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["domain"] == "AC"
    assert data["member_id"] == member_id
    assert data["total_controls_in_domain"] > 0
    assert data["created"] > 0
    assert data["created"] == data["total_controls_in_domain"] - data["skipped_already_assigned"]


@pytest.mark.anyio
async def test_domain_assignment_invalid_domain():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        member_resp = await ac.post(
            "/api/team/members",
            json={"name": "Domain Bad", "email": "domainbad@agi.example", "role": "Other"},
        )
        member_id = member_resp.json()["id"]

        resp = await ac.post(
            "/api/team/assignments/domain/ZZNOTREAL",
            params={"member_id": member_id},
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_workload_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/team/workload")
    assert resp.status_code == 200
    data = resp.json()
    assert "coverage" in data
    assert "member_workload" in data
    assert "unloaded_members" in data
    assert "shared_ownership_controls" in data

    cov = data["coverage"]
    assert "total_controls" in cov
    assert "owned_controls" in cov
    assert "unowned_controls" in cov
    assert "coverage_pct" in cov
    assert 0.0 <= cov["coverage_pct"] <= 100.0

    # Each member workload entry should have expected fields
    for mw in data["member_workload"]:
        assert "member_id" in mw
        assert "name" in mw
        assert "total_assigned" in mw
        assert "by_priority" in mw
        assert "by_domain" in mw
        assert "compliance_gap" in mw


@pytest.mark.anyio
async def test_poam_has_owner_column():
    """POAM CSV should include real team owner names when assignments exist."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/reports/poam")
    assert resp.status_code == 200
    # Header row must still be present
    assert "Control ID,Domain" in resp.text
    assert "Responsible Party" in resp.text


@pytest.mark.anyio
async def test_ssp_has_control_owner():
    """SSP Markdown should include 'Control Owner' for each assessment finding."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ensure at least one assessment exists so the findings section is non-empty
        await ac.patch(
            "/api/controls/AC.1.001",
            json={"implementation_status": "partially_implemented", "notes": "SSP owner test"},
        )
        resp = await ac.get("/api/reports/ssp")
    assert resp.status_code == 200
    assert "# System Security Plan" in resp.text
    assert "Control Owner" in resp.text
