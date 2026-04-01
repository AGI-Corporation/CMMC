import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_api.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_api.db"):
        os.remove("./test_api.db")


@pytest.mark.anyio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_list_controls():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/controls/")
    assert response.status_code == 200
    data = response.json()
    assert "controls" in data
    assert data["total"] > 0
    # Check for AC.1.001 which should be seeded
    control_ids = [c["control"]["id"] for c in data["controls"]]
    assert "AC.1.001" in control_ids


@pytest.mark.anyio
async def test_update_and_score():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Check SPRS score initial
        response = await ac.get("/api/assessment/sprs")
        data = response.json()
        initial_score = data["sprs_score"]

        # 2. Update to implemented
        update_data = {
            "implementation_status": "implemented",
            "notes": "Test fix",
            "responsible_party": "Tester",
        }
        patch_response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert patch_response.status_code == 200

        # 3. Check SPRS score again
        response = await ac.get("/api/assessment/sprs")
        data = response.json()
        # AC.1.001 has deduction 3.
        assert data["sprs_score"] == initial_score + 3


@pytest.mark.anyio
async def test_reports():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Check dashboard
        resp = await ac.get("/api/reports/dashboard")
        assert resp.status_code == 200

        # 2. Check SSP
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        assert "# System Security Plan" in resp.text

        # 3. Check POAM
        resp = await ac.get("/api/reports/poam")
        assert resp.status_code == 200
        assert "Control ID,Domain" in resp.text


@pytest.mark.anyio
async def test_update_with_advanced_fields():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        update_data = {
            "implementation_status": "implemented",
            "notes": "Advanced update",
            "responsible_party": "Tester",
            "confidence": 0.95,
            "poam_required": False,
            "evidence_ids": ["ev-123"],
        }
        patch_response = await ac.patch("/api/controls/AC.1.002", json=update_data)
        assert patch_response.status_code == 200
        data = patch_response.json()
        assert data["confidence"] == 0.95
        assert data["poam_required"] == False

        # Verify detail endpoint reflects these
        detail_response = await ac.get("/api/controls/AC.1.002")
        data = detail_response.json()
        assert data["confidence"] == 0.95
        assert data["evidence_count"] == 1
        assert data["poam_required"] == False


@pytest.mark.anyio
async def test_promote_icam_run():
    """Promote an ICAM agent run — uses standard results format."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Trigger an ICAM assessment to create an AgentRunRecord
        assess_resp = await ac.get("/api/agents/icam/assess")
        assert assess_resp.status_code == 200

        from sqlalchemy import select

        from backend.db.database import AgentRunRecord, AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(AgentRunRecord)
                .where(AgentRunRecord.agent_type == "icam")
                .order_by(AgentRunRecord.created_at.desc())
            )
            run = res.scalars().first()
            run_id = run.id

        promote_resp = await ac.post(f"/api/assessment/promote/{run_id}")
        assert promote_resp.status_code == 200
        data = promote_resp.json()
        assert data["status"] == "promoted"
        assert data["agent_type"] == "icam"
        assert data["assessments_created"] > 0


@pytest.mark.anyio
async def test_promote_data_agent_run():
    """Promote a data_protection agent run — generic standard format handler."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        assess_resp = await ac.get("/api/agents/data/assess")
        assert assess_resp.status_code == 200

        from sqlalchemy import select

        from backend.db.database import AgentRunRecord, AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(AgentRunRecord)
                .where(AgentRunRecord.agent_type == "data_protection")
                .order_by(AgentRunRecord.created_at.desc())
            )
            run = res.scalars().first()
            run_id = run.id

        promote_resp = await ac.post(f"/api/assessment/promote/{run_id}")
        assert promote_resp.status_code == 200
        data = promote_resp.json()
        assert data["status"] == "promoted"
        assert data["agent_type"] == "data_protection"
        assert data["assessments_created"] > 0


@pytest.mark.anyio
async def test_promote_remediation_agent_run():
    """Promote a remediation agent run — generic standard format handler."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        assess_resp = await ac.get("/api/agents/remediation/assess")
        assert assess_resp.status_code == 200

        from sqlalchemy import select

        from backend.db.database import AgentRunRecord, AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(AgentRunRecord)
                .where(AgentRunRecord.agent_type == "remediation")
                .order_by(AgentRunRecord.created_at.desc())
            )
            run = res.scalars().first()
            run_id = run.id

        promote_resp = await ac.post(f"/api/assessment/promote/{run_id}")
        assert promote_resp.status_code == 200
        data = promote_resp.json()
        assert data["status"] == "promoted"
        assert data["agent_type"] == "remediation"
        assert data["assessments_created"] > 0


@pytest.mark.anyio
async def test_hipaa_mapping():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/hipaa/mapping")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_safeguards"] > 0
    assert "mapping" in data
    hipaa_ids = [m["hipaa_id"] for m in data["mapping"]]
    assert "164.308(a)(1)" in hipaa_ids
    assert "164.312(a)(1)" in hipaa_ids


@pytest.mark.anyio
async def test_hipaa_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/hipaa/assess")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_safeguards" in data
    assert data["total_safeguards"] > 0
    assert "satisfied" in data
    assert "partially_satisfied" in data
    assert "gap" in data
    assert "overall_compliance_pct" in data
    assert "safeguards" in data
    # Verify each result has expected fields
    for s in data["safeguards"]:
        assert "hipaa_id" in s
        assert "hipaa_status" in s
        assert s["hipaa_status"] in ("satisfied", "partially_satisfied", "gap")


@pytest.mark.anyio
async def test_hipaa_gaps():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/hipaa/gaps")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_gaps" in data
    assert "gaps" in data
    # All items returned must be non-satisfied
    for g in data["gaps"]:
        assert g["hipaa_status"] != "satisfied"


@pytest.mark.anyio
async def test_hipaa_safeguard_detail():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/hipaa/safeguard/164.312(a)(1)")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hipaa_id"] == "164.312(a)(1)"
    assert "cmmc_control_details" in data
    assert len(data["cmmc_control_details"]) > 0


@pytest.mark.anyio
async def test_hipaa_safeguard_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/hipaa/safeguard/999.999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_oscal_export():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/oscal")
    assert resp.status_code == 200
    data = resp.json()
    ssp = data["system-security-plan"]
    assert "uuid" in ssp
    assert "metadata" in ssp
    assert "system-characteristics" in ssp
    assert "system-implementation" in ssp
    assert "control-implementation" in ssp
    impl = ssp["control-implementation"]
    assert len(impl["implemented-requirements"]) > 0
    # Verify OSCAL shape for one requirement
    req = impl["implemented-requirements"][0]
    assert "control-id" in req
    assert "statements" in req


@pytest.mark.anyio
async def test_dashboard_includes_remediation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    agent_names = [a["name"] for a in data["agents"]]
    assert "remediation" in agent_names

