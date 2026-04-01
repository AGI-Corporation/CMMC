import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import AsyncSessionLocal, Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agents.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_agents.db"):
        os.remove("./test_agents.db")


@pytest.mark.anyio
async def test_icam_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/icam/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "icam"
    assert len(data["assessments"]) > 0


@pytest.mark.anyio
async def test_devsecops_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/devsecops/assess/test-service")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "devsecops"
    assert "image_scan" in data


@pytest.mark.anyio
async def test_orchestrator_scorecard():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/orchestrator/scorecard")
    assert response.status_code == 200
    data = response.json()
    assert "scorecard" in data
    assert "sprs" in data


@pytest.mark.anyio
async def test_mistral_gap_analysis_mock():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        req = {
            "control_id": "AC.1.001",
            "control_title": "Limit access",
            "control_description": "Desc",
            "zt_pillar": "User",
        }
        response = await ac.post("/api/agents/mistral/gap-analysis", json=req)
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    if not os.getenv("MISTRAL_API_KEY"):
        assert "Mock analysis" in data["analysis"]["gap_summary"]


@pytest.mark.anyio
async def test_agent_run_promotion():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Trigger an agent run (ICAM)
        assess_resp = await ac.get("/api/agents/icam/assess")
        assert assess_resp.status_code == 200

        # 2. Get the run ID from the database
        from sqlalchemy import select

        from backend.db.database import AgentRunRecord

        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(AgentRunRecord).order_by(AgentRunRecord.created_at.desc())
            )
            run = res.scalars().first()
            run_id = run.id

        # 3. Promote the run
        promote_resp = await ac.post(f"/api/assessment/promote/{run_id}")
        assert promote_resp.status_code == 200
        assert promote_resp.json()["status"] == "promoted"
        assert promote_resp.json()["assessments_created"] > 0

        # 4. Verify assessment exists for one of the controls
        # ICAM evaluates IA.3.083
        detail_resp = await ac.get("/api/controls/IA.3.083")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert data["implementation_status"] == "partially_implemented"
        assert "Promoted from icam" in data["notes"]


# ─── New Agent Tests ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_data_agent_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/data/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "data_protection"
    assert data["zt_pillar"] == "Data"
    assert len(data["assessments"]) > 0
    control_ids = [a["control_id"] for a in data["assessments"]]
    assert "SC.3.177" in control_ids
    assert "AU.2.041" in control_ids


@pytest.mark.anyio
async def test_data_agent_stores():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/data/stores")
    assert response.status_code == 200
    data = response.json()
    assert "total_stores" in data
    assert "cui_stores" in data
    assert data["total_stores"] > 0


@pytest.mark.anyio
async def test_infra_agent_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/infra/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "infrastructure"
    assert "Device" in data["zt_pillars"]
    assert "Network" in data["zt_pillars"]
    assert len(data["assessments"]) > 0
    control_ids = [a["control_id"] for a in data["assessments"]]
    assert "CM.2.061" in control_ids
    assert "SC.3.177" in control_ids


@pytest.mark.anyio
async def test_infra_agent_network_topology():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/infra/network-topology")
    assert response.status_code == 200
    data = response.json()
    assert "total_segments" in data
    assert "segments" in data
    assert data["total_segments"] > 0


@pytest.mark.anyio
async def test_infra_agent_devices():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/infra/devices")
    assert response.status_code == 200
    data = response.json()
    assert "total_devices" in data
    assert data["total_devices"] > 0


@pytest.mark.anyio
async def test_governance_agent_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/governance/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "governance"
    assert len(data["assessments"]) > 0
    control_ids = [a["control_id"] for a in data["assessments"]]
    assert "CA.2.157" in control_ids
    assert "RA.2.141" in control_ids


@pytest.mark.anyio
async def test_governance_risk_posture():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/governance/risk-posture")
    assert response.status_code == 200
    data = response.json()
    assert "total_risks" in data
    assert "open_risks" in data
    assert data["total_risks"] > 0


@pytest.mark.anyio
async def test_governance_policies():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/governance/policies")
    assert response.status_code == 200
    data = response.json()
    assert "total_policies" in data
    assert data["total_policies"] > 0


@pytest.mark.anyio
async def test_governance_poam_priorities():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/governance/poam-priorities")
    assert response.status_code == 200
    data = response.json()
    assert "poam_items" in data
    assert "total_items" in data


@pytest.mark.anyio
async def test_ops_agent_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/ops/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "operations"
    assert data["zt_pillar"] == "Automation & Orchestration"
    assert len(data["assessments"]) > 0
    control_ids = [a["control_id"] for a in data["assessments"]]
    assert "IR.2.092" in control_ids
    assert "AU.2.041" in control_ids


@pytest.mark.anyio
async def test_ops_agent_siem_status():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/ops/siem-status")
    assert response.status_code == 200
    data = response.json()
    assert "total_sources" in data
    assert "enabled_sources" in data
    assert data["total_sources"] > 0


@pytest.mark.anyio
async def test_ops_agent_incidents():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/ops/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "total_incidents" in data
    assert data["total_incidents"] > 0


@pytest.mark.anyio
async def test_ops_agent_incident_triage():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/agents/ops/incident/triage",
            json={
                "incident_type": "unauthorized_access",
                "description": "Credential stuffing detected on admin portal",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "severity" in data
    assert "immediate_actions" in data
    assert "cmmc_controls_engaged" in data
    assert len(data["immediate_actions"]) > 0
    assert "IR.2.092" in data["cmmc_controls_engaged"]


@pytest.mark.anyio
async def test_orchestrator_run_manual():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/orchestrator/run",
            params={"trigger": "manual", "scope": "test-system"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "task_id" in data
    assert data["total_assessments"] >= 0


@pytest.mark.anyio
async def test_orchestrator_webhook_code_push():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/orchestrator/webhook/code-push",
            json={
                "service": "cmmc-api",
                "branch": "main",
                "commit_sha": "abc1234",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["event"] == "code_push"
    assert data["service"] == "cmmc-api"
    assert data["status"] == "completed"
    assert "assessments_run" in data


@pytest.mark.anyio
async def test_orchestrator_webhook_incident():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/orchestrator/webhook/incident",
            json={
                "incident_type": "ransomware",
                "description": "Ransomware indicators detected on file server",
                "severity": "P1",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["event"] == "incident"
    assert data["status"] == "completed"
    assert "IR.2.092" in data["ir_controls_engaged"]


@pytest.mark.anyio
async def test_orchestrator_run_assessment_trigger():
    """Full ASSESSMENT trigger runs all agents."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/orchestrator/run",
            params={"trigger": "assessment", "scope": "full-cmmc-assessment"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    # All six pillar agents should have contributed findings
    assert data["total_assessments"] > 0
    owner_agents = {
        r.get("owner_agent")
        for r in data["findings"].get("results", [])
        if "owner_agent" in r
    }
    assert "icam" in owner_agents
    assert "data_protection" in owner_agents
    assert "infrastructure" in owner_agents
    assert "remediation" in owner_agents


# ─── Remediation Agent Tests ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_remediation_agent_assess():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/remediation/assess")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "remediation"
    assert data["zt_pillar"] == "Automation & Orchestration"
    assert len(data["assessments"]) > 0
    control_ids = [a["control_id"] for a in data["assessments"]]
    assert "CM.2.061" in control_ids
    assert "SI.2.214" in control_ids
    assert "IR.2.093" in control_ids
    assert "CA.2.157" in control_ids


@pytest.mark.anyio
async def test_remediation_agent_status():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/remediation/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_items" in data
    assert "by_status" in data
    assert "by_priority" in data
    assert "overdue_count" in data
    assert data["total_items"] > 0


@pytest.mark.anyio
async def test_remediation_agent_playbook():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/remediation/playbook/SI.2.214")
    assert response.status_code == 200
    data = response.json()
    assert data["control_id"] == "SI.2.214"
    pb = data["playbook"]
    assert "title" in pb
    assert "steps" in pb
    assert len(pb["steps"]) > 0
    assert "validation_check" in pb
    assert "estimated_effort_hours" in pb


@pytest.mark.anyio
async def test_remediation_agent_playbook_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/agents/remediation/playbook/XX.9.999")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_remediation_agent_execute():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/agents/remediation/remediate/CM.2.062")
    assert response.status_code == 200
    data = response.json()
    assert data["control_id"] == "CM.2.062"
    assert data["status"] == "in_progress"
    assert "steps_initiated" in data
    assert len(data["steps_initiated"]) > 0
    assert "validation_check" in data


@pytest.mark.anyio
async def test_remediation_agent_ingest():
    findings = [
        {"control_id": "RA.2.141", "status": "not_implemented", "findings": ["No risk assessment process"]},
        {"control_id": "CM.2.061", "status": "partially_implemented", "findings": ["Baseline drift detected"]},
        {"control_id": "AC.1.001", "status": "implemented", "findings": []},
    ]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/agents/remediation/ingest", json=findings)
    assert response.status_code == 200
    data = response.json()
    assert data["ingested"] == 3
    # Only not_implemented / partially_implemented without existing open records create new items
    assert "new_remediation_items" in data
    assert "items" in data

