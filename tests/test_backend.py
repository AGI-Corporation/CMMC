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
