"""
Evidence Router Tests
Covers: create, list (with filters), get by ID, delete, 404 paths, all evidence types.
"""
import pytest
import os
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_evidence.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_evidence.db"):
        os.remove("./test_evidence.db")


@pytest.mark.anyio
async def test_create_evidence():
    """Create an evidence artifact and verify the returned fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "control_id": "AC.1.001",
            "zt_pillar": "User",
            "zt_capability_id": "ZT-1.1",
            "evidence_type": "log",
            "title": "Access Log Evidence",
            "description": "Log file showing access control enforcement",
            "source_system": "SIEM",
            "uri": "s3://evidence/access-log.gz",
            "reviewer": "ISSO",
            "review_cycle_days": 90,
        }
        response = await ac.post("/api/evidence/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["control_id"] == "AC.1.001"
    assert data["evidence_type"] == "log"
    assert data["title"] == "Access Log Evidence"
    assert data["zt_pillar"] == "User"
    assert data["zt_capability_id"] == "ZT-1.1"
    assert "id" in data
    assert data["id"] != ""


@pytest.mark.anyio
async def test_list_evidence_returns_created():
    """After creating evidence, list should return at least one item."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/evidence/")
    assert response.status_code == 200
    data = response.json()
    assert "evidence" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["evidence"]) == data["total"]


@pytest.mark.anyio
async def test_list_evidence_filter_by_control_id():
    """Filter evidence by control_id returns only matching items."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create evidence for a different control
        payload = {
            "control_id": "IA.1.076",
            "zt_pillar": "User",
            "evidence_type": "policy",
            "title": "Authentication Policy",
            "description": "Policy doc for IA controls",
            "source_system": "PolicyManager",
        }
        await ac.post("/api/evidence/", json=payload)

        response = await ac.get("/api/evidence/", params={"control_id": "IA.1.076"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(e["control_id"] == "IA.1.076" for e in data["evidence"])


@pytest.mark.anyio
async def test_list_evidence_filter_by_zt_pillar():
    """Filter evidence by zt_pillar returns only matching items."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create evidence for a Device pillar control
        payload = {
            "control_id": "CM.2.061",
            "zt_pillar": "Device",
            "evidence_type": "scan",
            "title": "Config Scan",
            "description": "CIS Benchmark scan",
            "source_system": "Nessus",
        }
        await ac.post("/api/evidence/", json=payload)

        response = await ac.get("/api/evidence/", params={"zt_pillar": "Device"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(e["zt_pillar"] == "Device" for e in data["evidence"])


@pytest.mark.anyio
async def test_list_evidence_filter_by_evidence_type():
    """Filter evidence by evidence_type returns only matching items."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/evidence/", params={"evidence_type": "policy"})
    assert response.status_code == 200
    data = response.json()
    assert all(e["evidence_type"] == "policy" for e in data["evidence"])


@pytest.mark.anyio
async def test_get_evidence_by_id():
    """Create evidence, then retrieve it by ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "control_id": "SI.1.210",
            "zt_pillar": "Application",
            "evidence_type": "report",
            "title": "Vulnerability Report",
            "description": "Monthly vuln scan report",
            "source_system": "Qualys",
        }
        create_resp = await ac.post("/api/evidence/", json=payload)
        assert create_resp.status_code == 200
        evidence_id = create_resp.json()["id"]

        get_resp = await ac.get(f"/api/evidence/{evidence_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == evidence_id
    assert data["control_id"] == "SI.1.210"
    assert data["title"] == "Vulnerability Report"


@pytest.mark.anyio
async def test_get_evidence_not_found():
    """Getting a non-existent evidence ID returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/evidence/does-not-exist-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_evidence():
    """Create evidence, delete it, then verify it is gone."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "control_id": "AU.2.041",
            "zt_pillar": "Visibility & Analytics",
            "evidence_type": "log",
            "title": "Audit Log",
            "description": "Audit log evidence",
            "source_system": "Splunk",
        }
        create_resp = await ac.post("/api/evidence/", json=payload)
        evidence_id = create_resp.json()["id"]

        delete_resp = await ac.delete(f"/api/evidence/{evidence_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["deleted"] == evidence_id

        get_resp = await ac.get(f"/api/evidence/{evidence_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_evidence_not_found():
    """Deleting a non-existent evidence ID returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/api/evidence/non-existent-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_evidence_all_types():
    """All valid EvidenceType values are accepted."""
    evidence_types = [
        "log", "scan", "policy", "diagram",
        "screenshot", "report", "interview", "configuration",
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for ev_type in evidence_types:
            payload = {
                "control_id": "AC.1.001",
                "zt_pillar": "User",
                "evidence_type": ev_type,
                "title": f"Evidence ({ev_type})",
                "description": f"Test evidence of type {ev_type}",
                "source_system": "TestSystem",
            }
            response = await ac.post("/api/evidence/", json=payload)
            assert response.status_code == 200, f"Failed for type {ev_type}"
            assert response.json()["evidence_type"] == ev_type


@pytest.mark.anyio
async def test_create_evidence_invalid_type():
    """An invalid evidence_type value returns a validation error."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "control_id": "AC.1.001",
            "zt_pillar": "User",
            "evidence_type": "invalid_type",
            "title": "Bad Type",
            "description": "Should fail",
            "source_system": "System",
        }
        response = await ac.post("/api/evidence/", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_evidence_metadata_stored():
    """Metadata dict is stored and returned correctly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "control_id": "AC.1.001",
            "zt_pillar": "User",
            "evidence_type": "screenshot",
            "title": "Screenshot with metadata",
            "description": "Dashboard screenshot",
            "source_system": "Grafana",
            "metadata": {"dashboard": "compliance", "version": "2.0"},
        }
        response = await ac.post("/api/evidence/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["dashboard"] == "compliance"
    assert data["metadata"]["version"] == "2.0"
