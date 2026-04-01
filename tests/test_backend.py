import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app
from backend.middleware.rate_limit import reset_all_windows


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
    # Flush rate-limit windows so the test suite starts with a clean slate
    reset_all_windows()
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
    assert "supply_chain" in agent_names


# ─── Supply Chain Agent Tests ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_supply_chain_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/supply-chain/assess")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "supply_chain"
    assert data["zt_pillar"] == "Application"
    control_ids = [a["control_id"] for a in data["assessments"]]
    assert "SR.1.001" in control_ids
    assert "SR.1.002" in control_ids
    assert "SR.2.070" in control_ids
    assert "SR.2.111" in control_ids


@pytest.mark.anyio
async def test_supply_chain_vendors():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/supply-chain/vendors")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_vendors" in data
    assert data["total_vendors"] > 0
    assert "risk_summary" in data
    assert "suspended" in data["risk_summary"]


@pytest.mark.anyio
async def test_supply_chain_vendors_filter():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/supply-chain/vendors?status=suspended")
    assert resp.status_code == 200
    data = resp.json()
    for v in data["vendors"]:
        assert v["status"] == "suspended"


@pytest.mark.anyio
async def test_supply_chain_vendor_risk_analysis():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/supply-chain/analyze-risk/v005")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vendor_id"] == "v005"
    # v005 has China in countries_of_origin
    assert "China" in data["adversary_country_exposure"]
    assert len(data["risk_flags"]) > 0
    assert "cmmc_control_impact" in data


@pytest.mark.anyio
async def test_supply_chain_vendor_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/supply-chain/analyze-risk/v999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_supply_chain_disposal_records():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/supply-chain/disposal-records")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_records" in data
    assert "compliant" in data
    assert "non_compliant" in data
    assert data["total_records"] > 0


# ─── Blockchain Audit Ledger Tests ────────────────────────────────────────────


@pytest.mark.anyio
async def test_blockchain_initial_chain():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/blockchain/chain")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_transactions" in data
    assert "transactions" in data


@pytest.mark.anyio
async def test_blockchain_verify_empty_chain():
    """An empty chain should be valid."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/blockchain/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["violations_found"] == 0


@pytest.mark.anyio
async def test_blockchain_records_after_promote():
    """Promoting an agent run should add a transaction to the chain."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Get chain length before
        chain_resp = await ac.get("/api/blockchain/chain")
        before = chain_resp.json()["total_transactions"]

        # Trigger ICAM assessment then promote
        await ac.get("/api/agents/icam/assess")
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

        # Chain should be one longer
        chain_resp2 = await ac.get("/api/blockchain/chain")
        after = chain_resp2.json()["total_transactions"]
        assert after == before + 1


@pytest.mark.anyio
async def test_blockchain_verify_after_records():
    """Chain with at least one transaction should still verify as valid."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/blockchain/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True


@pytest.mark.anyio
async def test_blockchain_stats():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/blockchain/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_transactions" in data
    assert "events_by_type" in data
    assert "genesis_hash" in data


# ─── Evidence Review-Due Tests ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_evidence_review_due_fresh_evidence():
    """Newly created evidence should NOT appear in review-due."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create fresh evidence with 365-day cycle
        create_resp = await ac.post(
            "/api/evidence/",
            json={
                "control_id": "AC.1.001",
                "zt_pillar": "User",
                "evidence_type": "log",
                "title": "Fresh Evidence",
                "description": "Fresh evidence for review-due test",
                "source_system": "Test",
                "review_cycle_days": 365,
            },
        )
        assert create_resp.status_code == 200

        # Should not be in review-due yet
        due_resp = await ac.get("/api/evidence/review-due")
    assert due_resp.status_code == 200
    data = due_resp.json()
    evidence_ids = [e["id"] for e in data["evidence"]]
    fresh_id = create_resp.json()["id"]
    assert fresh_id not in evidence_ids


@pytest.mark.anyio
async def test_evidence_review_due_future_window():
    """Using days_overdue=730 should surface the fresh evidence."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create evidence with 365-day cycle
        create_resp = await ac.post(
            "/api/evidence/",
            json={
                "control_id": "AC.1.002",
                "zt_pillar": "User",
                "evidence_type": "policy",
                "title": "Window Evidence",
                "description": "Evidence for window review-due test",
                "source_system": "Test",
                "review_cycle_days": 1,
            },
        )
        assert create_resp.status_code == 200
        ev_id = create_resp.json()["id"]

        # days_overdue=730 → items due within next 730 days are included
        due_resp = await ac.get("/api/evidence/review-due?days_overdue=730")
    assert due_resp.status_code == 200
    data = due_resp.json()
    evidence_ids = [e["id"] for e in data["evidence"]]
    assert ev_id in evidence_ids


# ─── Rate Limiter Tests ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_rate_limit_headers_present():
    """Responses should include X-RateLimit-* headers on non-exempt paths."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/controls/")
    assert resp.status_code == 200
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers
    assert "x-ratelimit-reset" in resp.headers


@pytest.mark.anyio
async def test_rate_limit_exempt_health():
    """Health endpoint is exempt — should NOT have rate-limit headers."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    # Exempt path: no rate-limit headers
    assert "x-ratelimit-limit" not in resp.headers




# ─── Expanded Catalog Tests ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_catalog_has_all_domains():
    """All 14 CMMC domains + SR should be present in the seeded catalog."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/controls/")
    assert resp.status_code == 200
    data = resp.json()
    domains = {c["control"]["domain"] for c in data["controls"]}
    expected = {"AC", "AU", "CA", "CM", "IA", "IR", "MA", "MP", "PE", "PS", "RA", "SA", "SC", "SI", "SR"}
    assert expected.issubset(domains), f"Missing domains: {expected - domains}"


@pytest.mark.anyio
async def test_catalog_control_count():
    """Catalog should have at least 70 controls after expansion."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/controls/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 70, f"Expected ≥70 controls, got {data['total']}"


@pytest.mark.anyio
async def test_catalog_domain_filter_au():
    """AU domain filter should return only AU controls."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/controls/?domain=AU")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 4
    for c in data["controls"]:
        assert c["control"]["domain"] == "AU"


@pytest.mark.anyio
async def test_catalog_domain_filter_sr():
    """SR domain filter should return supply chain controls."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/controls/?domain=SR")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 4
    control_ids = [c["control"]["id"] for c in data["controls"]]
    assert "SR.1.001" in control_ids
    assert "SR.2.111" in control_ids


# ─── Assessment Submit Tests ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_assessment_submit_implemented():
    """Submit an 'implemented' assessment and verify response."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "AC.1.001",
                "status": "implemented",
                "confidence": 0.95,
                "notes": "Implemented via LDAP with RBAC.",
                "assessor": "test-assessor",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "AC.1.001"
    assert data["status"] == "implemented"
    assert data["confidence"] == 0.95
    assert data["poam_required"] is False
    assert "submission_id" in data
    assert "blockchain_tx_id" in data
    assert data["blockchain_tx_id"] is not None


@pytest.mark.anyio
async def test_assessment_submit_not_implemented_triggers_poam():
    """not_implemented status should auto-flag poam_required."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "IA.3.083",
                "status": "not_implemented",
                "confidence": 0.0,
                "assessor": "test-assessor",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["poam_required"] is True


@pytest.mark.anyio
async def test_assessment_submit_partially_implemented_triggers_poam():
    """partially_implemented should auto-flag poam_required."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "SC.3.177",
                "status": "partially_implemented",
                "confidence": 0.4,
                "assessor": "test-assessor",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["poam_required"] is True


@pytest.mark.anyio
async def test_assessment_submit_invalid_status():
    """Unknown status should return 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "AC.1.001",
                "status": "unicorn",
                "confidence": 0.5,
            },
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_assessment_submit_invalid_confidence():
    """Confidence > 1.0 should return 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "AC.1.001",
                "status": "implemented",
                "confidence": 1.5,
            },
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_assessment_submit_unknown_control():
    """Submitting for a non-existent control should return 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "XX.9.999",
                "status": "implemented",
                "confidence": 0.9,
            },
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_assessment_submit_blockchain_recorded():
    """Each submission should add a transaction to the blockchain."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        chain_before = (await ac.get("/api/blockchain/chain")).json()["total_transactions"]
        await ac.post(
            "/api/assessment/submit",
            json={"control_id": "AU.2.041", "status": "implemented", "confidence": 0.8},
        )
        chain_after = (await ac.get("/api/blockchain/chain")).json()["total_transactions"]
    assert chain_after == chain_before + 1


# ─── Assessment History Tests ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_assessment_history_returns_submissions():
    """History endpoint should return previously submitted assessments."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Submit a couple assessments for the same control
        await ac.post(
            "/api/assessment/submit",
            json={"control_id": "CM.2.061", "status": "planned", "confidence": 0.3},
        )
        await ac.post(
            "/api/assessment/submit",
            json={"control_id": "CM.2.061", "status": "implemented", "confidence": 0.9},
        )
        resp = await ac.get("/api/assessment/history/CM.2.061")
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "CM.2.061"
    assert data["total_assessments"] >= 2
    assert "history" in data
    assert len(data["history"]) >= 2
    # Most recent first
    statuses = [h["status"] for h in data["history"]]
    assert "implemented" in statuses


@pytest.mark.anyio
async def test_assessment_history_unknown_control():
    """History for unknown control should return 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/history/XX.9.999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_assessment_history_empty():
    """Control with no assessments should return empty history list."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # SA.2.150 has no assessments in this test run
        resp = await ac.get("/api/assessment/history/SA.2.150")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_assessments"] == 0
    assert data["history"] == []


# ─── Agent Runs Listing Tests ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_agent_runs_returns_results():
    """After agent assessments, /runs should return records."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Trigger at least one run
        await ac.get("/api/agents/icam/assess")
        resp = await ac.get("/api/assessment/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "runs" in data
    assert data["total"] > 0
    # Each run should have required fields
    run = data["runs"][0]
    assert "run_id" in run
    assert "agent_type" in run
    assert "status" in run
    assert "trigger" in run


@pytest.mark.anyio
async def test_list_agent_runs_filter_by_agent():
    """Filter by agent_type=icam should return only ICAM runs."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/runs?agent_type=icam")
    assert resp.status_code == 200
    data = resp.json()
    for run in data["runs"]:
        assert run["agent_type"] == "icam"


@pytest.mark.anyio
async def test_list_agent_runs_filter_by_status():
    """Filter by status=completed should return only completed runs."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/runs?status=completed")
    assert resp.status_code == 200
    data = resp.json()
    for run in data["runs"]:
        assert run["status"] == "completed"


@pytest.mark.anyio
async def test_list_agent_runs_pagination():
    """Pagination (limit/offset) should work correctly."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        all_resp = await ac.get("/api/assessment/runs?limit=200")
        total = all_resp.json()["total"]

        page1 = await ac.get("/api/assessment/runs?limit=2&offset=0")
        page2 = await ac.get("/api/assessment/runs?limit=2&offset=2")

    p1 = page1.json()
    p2 = page2.json()
    assert p1["total"] == total
    assert len(p1["runs"]) <= 2
    # Pages should not overlap
    p1_ids = {r["run_id"] for r in p1["runs"]}
    p2_ids = {r["run_id"] for r in p2["runs"]}
    assert p1_ids.isdisjoint(p2_ids)


# ─── AT Domain + Awareness Agent Tests ────────────────────────────────────────


@pytest.mark.anyio
async def test_catalog_has_at_domain():
    """AT domain controls should be present after catalog expansion."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/controls/?domain=AT")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    ids = [c["control"]["id"] for c in data["controls"]]
    assert "AT.2.056" in ids
    assert "AT.2.057" in ids
    assert "AT.3.058" in ids


@pytest.mark.anyio
async def test_awareness_agent_assess():
    """Awareness agent full assessment should return results for all 5 controls."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/awareness/assess")
    assert resp.status_code == 200
    data = resp.json()
    assert "agent" in data
    assert data["agent"] == "awareness"
    assert "assessments" in data
    control_ids = [r["control_id"] for r in data["assessments"]]
    assert "AT.2.056" in control_ids
    assert "AT.2.057" in control_ids
    assert "AT.3.058" in control_ids
    assert "PS.2.127" in control_ids
    assert "PS.2.128" in control_ids


@pytest.mark.anyio
async def test_awareness_agent_training_status():
    """Training status endpoint should return per-user records."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/awareness/training-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "personnel" in data
    assert "summary" in data
    assert len(data["personnel"]) >= 6
    user = data["personnel"][0]
    assert "awareness_status" in user
    assert "role_training_status" in user
    assert "insider_threat_status" in user
    assert "screening_status" in user


@pytest.mark.anyio
async def test_awareness_agent_personnel():
    """Personnel endpoint should return PS-focused data."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/awareness/personnel")
    assert resp.status_code == 200
    data = resp.json()
    assert "personnel" in data
    assert data["total"] >= 6
    # Should detect the terminated-with-no-access-revocation gap
    assert data["termination_gaps"] >= 1
    # Verify fields present
    p = data["personnel"][0]
    assert "screening_status" in p
    assert "termination_date" in p


@pytest.mark.anyio
async def test_awareness_agent_run_can_be_promoted():
    """Awareness agent runs should be promotable via /promote."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Trigger a fresh assessment
        await ac.get("/api/agents/awareness/assess")
        # Find the latest awareness run
        runs_resp = await ac.get("/api/assessment/runs?agent_type=awareness")
        runs_data = runs_resp.json()
        assert runs_data["total"] >= 1
        run_id = runs_data["runs"][0]["run_id"]
        promo = await ac.post(f"/api/assessment/promote/{run_id}")
    assert promo.status_code == 200
    data = promo.json()
    assert data["status"] == "promoted"
    assert data["assessments_created"] == 5  # one per AT/PS control


# ─── Evidence-Control Linkage Tests ───────────────────────────────────────────


@pytest.mark.anyio
async def test_link_evidence_to_control():
    """Link an evidence artifact to a control and verify the link."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create an evidence artifact
        ev_resp = await ac.post(
            "/api/evidence/",
            json={
                "control_id": "IA.1.076",
                "zt_pillar": "User",
                "zt_capability_id": "ZT-1.1",
                "evidence_type": "policy",
                "title": "Identity verification policy",
                "description": "Okta identity policy document.",
                "source_system": "Okta",
                "uri": "https://okta.example.com/policies/identity.pdf",
                "reviewer": "alice",
            },
        )
        assert ev_resp.status_code == 200
        ev_id = ev_resp.json()["id"]

        # Link to an additional control
        link_resp = await ac.post(
            f"/api/evidence/{ev_id}/link-control/IA.3.083"
        )
    assert link_resp.status_code == 200
    data = link_resp.json()
    assert data["evidence_id"] == ev_id
    assert data["control_id"] == "IA.3.083"
    assert data["linked"] is True


@pytest.mark.anyio
async def test_link_evidence_idempotent():
    """Linking the same evidence twice should return already_linked."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ev_resp = await ac.post(
            "/api/evidence/",
            json={
                "control_id": "AC.1.001",
                "zt_pillar": "User",
                "zt_capability_id": "ZT-1.2",
                "evidence_type": "log",
                "title": "Access control logs",
                "description": "Syslog showing AC.1.001 enforcement.",
                "source_system": "Splunk",
                "uri": "https://splunk.example.com/ac001.log",
                "reviewer": "bob",
            },
        )
        ev_id = ev_resp.json()["id"]
        # Submit an assessment that includes this evidence
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "SC.1.175",
                "status": "implemented",
                "confidence": 0.8,
                "evidence_ids": [ev_id],
            },
        )
        link1 = await ac.post(f"/api/evidence/{ev_id}/link-control/SC.1.175")
        link2 = await ac.post(f"/api/evidence/{ev_id}/link-control/SC.1.175")
    assert link1.status_code == 200
    assert link2.status_code == 200
    assert link2.json()["action"] == "already_linked"


@pytest.mark.anyio
async def test_link_evidence_unknown_evidence():
    """Linking nonexistent evidence should return 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/evidence/nonexistent-uuid/link-control/AC.1.001")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_link_evidence_unknown_control():
    """Linking to unknown control should return 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ev_resp = await ac.post(
            "/api/evidence/",
            json={
                "control_id": "AC.1.001",
                "zt_pillar": "User",
                "zt_capability_id": "ZT-1.3",
                "evidence_type": "scan",
                "title": "Vuln scan",
                "description": "Nessus scan.",
                "source_system": "Nessus",
                "uri": "https://nessus.example.com/scan1",
                "reviewer": "carol",
            },
        )
        ev_id = ev_resp.json()["id"]
        resp = await ac.post(f"/api/evidence/{ev_id}/link-control/ZZ.9.999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_control_evidence():
    """GET /api/controls/{id}/evidence should return linked evidence."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create evidence and link it via assessment submission
        ev_resp = await ac.post(
            "/api/evidence/",
            json={
                "control_id": "SI.1.210",
                "zt_pillar": "Application",
                "zt_capability_id": "ZT-5.1",
                "evidence_type": "scan",
                "title": "Patch scan results",
                "description": "Qualys patch compliance scan.",
                "source_system": "Qualys",
                "uri": "https://qualys.example.com/si1210",
                "reviewer": "dave",
            },
        )
        ev_id = ev_resp.json()["id"]
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "SI.1.210",
                "status": "implemented",
                "confidence": 0.9,
                "evidence_ids": [ev_id],
            },
        )
        list_resp = await ac.get("/api/controls/SI.1.210/evidence")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["control_id"] == "SI.1.210"
    assert data["evidence_count"] >= 1
    ev_ids_returned = [e["evidence_id"] for e in data["evidence"]]
    assert ev_id in ev_ids_returned


@pytest.mark.anyio
async def test_list_control_evidence_unknown():
    """GET /api/controls/{id}/evidence for unknown control returns 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/controls/ZZ.9.999/evidence")
    assert resp.status_code == 404


# ─── POAM Management Tests ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_poam_entries_returns_results():
    """After submitting not_implemented assessments, POAM list should return them."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Submit a not_implemented assessment (poam auto-flagged)
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "CA.2.157",
                "status": "not_implemented",
                "confidence": 0.0,
                "assessor": "poam-tester",
            },
        )
        resp = await ac.get("/api/assessment/poam")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "entries" in data
    assert data["total"] >= 1
    entry = data["entries"][0]
    assert "control_id" in entry
    assert "poam_status" in entry
    assert "status" in entry


@pytest.mark.anyio
async def test_list_poam_filter_by_domain():
    """POAM list should support domain filtering."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/poam?domain=CA")
    assert resp.status_code == 200
    data = resp.json()
    for entry in data["entries"]:
        assert entry["domain"] == "CA"


@pytest.mark.anyio
async def test_update_poam_entry():
    """PATCH /api/assessment/poam/{control_id} should update target date and notes."""
    from datetime import UTC, datetime, timedelta
    target = (datetime.now(UTC) + timedelta(days=90)).isoformat()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Ensure a POAM entry exists for CA.2.157
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "CA.2.157",
                "status": "not_implemented",
                "confidence": 0.0,
            },
        )
        resp = await ac.patch(
            "/api/assessment/poam/CA.2.157",
            json={
                "target_completion_date": target,
                "notes": "Remediation scheduled for Q3.",
                "responsible_party": "security-team",
                "poam_status": "in_progress",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] is True
    assert data["control_id"] == "CA.2.157"
    assert "new_assessment_id" in data
    assert data["notes"] is not None


@pytest.mark.anyio
async def test_update_poam_unknown_control():
    """PATCH /poam for unknown control should return 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.patch(
            "/api/assessment/poam/ZZ.9.999",
            json={"notes": "test"},
        )
    assert resp.status_code == 404


# ─── Compliance Trend Tests ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_compliance_trend_day():
    """Trend endpoint with window=day should return periods data points."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/trend?window=day&periods=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["window"] == "day"
    assert data["periods"] == 7
    assert len(data["data"]) == 7
    row = data["data"][0]
    assert "period_start" in row
    assert "period_end" in row
    assert "total_submissions" in row
    assert "implemented" in row


@pytest.mark.anyio
async def test_compliance_trend_week():
    """Trend endpoint with window=week should return weekly buckets."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/trend?window=week&periods=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["window"] == "week"
    assert len(data["data"]) == 4


@pytest.mark.anyio
async def test_compliance_trend_invalid_window():
    """Invalid window parameter should return 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/trend?window=month&periods=7")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_compliance_trend_recent_submissions_appear():
    """Assessments submitted today should appear in today's trend bucket."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Submit a fresh assessment
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "RA.2.141",
                "status": "implemented",
                "confidence": 0.88,
            },
        )
        resp = await ac.get("/api/assessment/trend?window=day&periods=1")
    assert resp.status_code == 200
    data = resp.json()
    today_bucket = data["data"][0]
    assert today_bucket["total_submissions"] >= 1
    assert today_bucket["implemented"] >= 1


# ─── ICAM Privileged Access Review Tests ──────────────────────────────────────


@pytest.mark.anyio
async def test_icam_assess_includes_privileged_and_lockout():
    """ICAM full assessment should now include IA.3.084 and AC.2.013 checks."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/icam/assess")
    assert resp.status_code == 200
    data = resp.json()
    control_ids = [r["control_id"] for r in data["assessments"]]
    assert "IA.3.083" in control_ids  # MFA coverage
    assert "AC.2.007" in control_ids  # least privilege
    assert "IA.3.084" in control_ids  # privileged access review
    assert "AC.2.013" in control_ids  # account lockout/dormancy


@pytest.mark.anyio
async def test_icam_privileged_access_endpoint():
    """GET /api/agents/icam/privileged-access should return privileged user data."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/agents/icam/privileged-access")
    assert resp.status_code == 200
    data = resp.json()
    assert "privileged_users" in data
    assert "strong_auth_count" in data
    assert "review_overdue_count" in data
    assert "records" in data
    assert data["privileged_users"] >= 1
    record = data["records"][0]
    assert "strong_auth" in record
    assert "review_overdue" in record
    assert "days_since_access_review" in record


# ─── Notification Service Tests ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_poam_submit_fires_notification():
    """Submitting a not_implemented assessment should fire a POAM notification."""
    from backend.services.notification_service import get_event_log, _event_log
    # Clear event log
    _event_log.clear()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "SC.1.175",
                "status": "not_implemented",
                "confidence": 0.0,
                "assessor": "notif-tester",
            },
        )
    events = get_event_log(event_type="poam_flagged")
    assert len(events) >= 1
    evt = events[0]
    assert evt["event_type"] == "poam_flagged"
    assert evt["control_id"] == "SC.1.175"
    assert evt["severity"] in ("critical", "high", "medium")


@pytest.mark.anyio
async def test_notifications_endpoint():
    """GET /api/assessment/notifications should return recent events."""
    from backend.services.notification_service import _event_log
    _event_log.clear()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Fire a POAM event
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "IA.2.078",
                "status": "not_implemented",
                "confidence": 0.1,
            },
        )
        resp = await ac.get("/api/assessment/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert data["total"] >= 1


@pytest.mark.anyio
async def test_notifications_filter():
    """Notification endpoint should support event_type and severity filtering."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            "/api/assessment/notifications?event_type=poam_flagged&severity=high"
        )
    assert resp.status_code == 200
    data = resp.json()
    for evt in data["events"]:
        assert evt["event_type"] == "poam_flagged"
        assert evt["severity"] == "high"


@pytest.mark.anyio
async def test_implemented_submit_no_notification():
    """Submitting an implemented assessment should NOT fire a POAM notification."""
    from backend.services.notification_service import _event_log
    _event_log.clear()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/api/assessment/submit",
            json={
                "control_id": "AC.1.001",
                "status": "implemented",
                "confidence": 0.95,
            },
        )
    from backend.services.notification_service import get_event_log
    events = get_event_log(event_type="poam_flagged")
    assert len(events) == 0


# ─── Assessment Summary Tests ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_assessment_summary():
    """GET /api/assessment/summary should return per-domain stats."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Submit a few assessments across domains first
        for control_id, status in [
            ("AC.1.001", "implemented"),
            ("IA.1.076", "not_implemented"),
            ("AT.2.056", "partially_implemented"),
        ]:
            await ac.post(
                "/api/assessment/submit",
                json={"control_id": control_id, "status": status, "confidence": 0.5},
            )
        resp = await ac.get("/api/assessment/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "sprs_score" in data
    assert "total_controls" in data
    assert "domains" in data
    assert len(data["domains"]) >= 1
    domain_names = [d["domain"] for d in data["domains"]]
    assert "AC" in domain_names
    # Each domain entry has required fields
    domain = data["domains"][0]
    assert "total_controls" in domain
    assert "implemented" in domain
    assert "sprs_deduction" in domain
    assert "compliance_pct" in domain


@pytest.mark.anyio
async def test_assessment_summary_sorted_by_sprs_deduction():
    """Domains should be sorted by SPRS deduction descending."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/assessment/summary")
    data = resp.json()
    deductions = [d["sprs_deduction"] for d in data["domains"]]
    assert deductions == sorted(deductions, reverse=True)


# ─── Maturity Heatmap Tests ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_maturity_heatmap_structure():
    """GET /api/reports/maturity-heatmap should return pillar_rollup and matrix."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/maturity-heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert "pillar_rollup" in data
    assert "matrix" in data
    assert "generated_at" in data
    assert len(data["pillar_rollup"]) == 7  # 7 ZT pillars
    rollup = data["pillar_rollup"][0]
    assert "pillar" in rollup
    assert "domains" in rollup
    assert "maturity_score" in rollup
    assert "total_controls" in rollup
    assert "implemented" in rollup
    assert "avg_confidence" in rollup


@pytest.mark.anyio
async def test_maturity_heatmap_user_pillar_includes_at():
    """User pillar in heatmap should include AT domain (added in session 2)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/maturity-heatmap")
    data = resp.json()
    user_pillar = next(p for p in data["pillar_rollup"] if p["pillar"] == "User")
    assert "AT" in user_pillar["domains"]


@pytest.mark.anyio
async def test_maturity_heatmap_sorted_ascending():
    """Pillars in heatmap should be sorted by maturity_score ascending (lowest first)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/maturity-heatmap")
    data = resp.json()
    scores = [p["maturity_score"] for p in data["pillar_rollup"]]
    assert scores == sorted(scores)


@pytest.mark.anyio
async def test_maturity_heatmap_cell_fields():
    """Each matrix cell should have pillar, domain, maturity_score, avg_confidence."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/maturity-heatmap")
    data = resp.json()
    for cell in data["matrix"]:
        assert "pillar" in cell
        assert "domain" in cell
        assert "total_controls" in cell
        assert "implemented" in cell
        assert "avg_confidence" in cell
        assert "maturity_score" in cell


# ─── Dashboard AT/Awareness Integration Test ──────────────────────────────────


@pytest.mark.anyio
async def test_dashboard_includes_awareness_agent_and_at_domain():
    """Dashboard should list awareness agent and AT in User pillar domains."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/reports/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    agent_names = [a["name"] for a in data["agents"]]
    assert "awareness" in agent_names
    user_pillar = next(p for p in data["zt_pillars"] if p["pillar"] == "User")
    assert "AT" in user_pillar["domains"]


# ─── Orchestrator ASSESSMENT trigger includes Awareness ─────────────────────


@pytest.mark.anyio
async def test_orchestrator_task_includes_awareness():
    """Creating an ASSESSMENT task should include awareness agent."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/orchestrator/task?trigger=assessment&scope=full-system"
        )
    assert resp.status_code == 200
    data = resp.json()
    agents = data.get("assigned_agents", [])
    assert "awareness" in agents


@pytest.mark.anyio
async def test_orchestrator_schedule_trigger_includes_awareness():
    """SCHEDULE trigger should also include awareness agent."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/orchestrator/task?trigger=schedule&scope=scheduled-review"
        )
    assert resp.status_code == 200
    data = resp.json()
    agents = data.get("assigned_agents", [])
    assert "awareness" in agents
