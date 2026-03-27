"""
Extended API Coverage Tests
Covers:
  - API: /api/agents/icam/users
  - API: /api/agents/devsecops/scan-image (clean + vulnerable + base image)
  - API: /api/agents/devsecops/sbom/{service_name}
  - API: /api/orchestrator/task (manual, code_push, incident, with controls)
  - API: /api/orchestrator/report
  - API: /api/agents/mistral/code-review
  - API: /api/agents/mistral/ask
  - API: /api/agents/mistral/gap-analysis with evidence

Pure agent unit tests are in test_agent_pure_units.py.
"""
import pytest
import os

from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base



@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agent_units.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_agent_units.db"):
        os.remove("./test_agent_units.db")


# ─────────────────────────────────────────────────────────────────────────────
# ICAM users
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_icam_users_endpoint():
    """ICAM user inventory endpoint returns correct structure."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/agents/icam/users")
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "mfa_coverage_pct" in data
    assert "privileged_users" in data
    assert "users" in data
    assert data["total_users"] > 0
    for user in data["users"]:
        assert "user_id" in user
        assert "username" in user
        assert "mfa_enabled" in user
        assert "privileged" in user


@pytest.mark.anyio
async def test_icam_users_mfa_pct_range():
    """MFA coverage percentage is between 0 and 100."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/agents/icam/users")
    data = response.json()
    assert 0.0 <= data["mfa_coverage_pct"] <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# DevSecOps scan-image / SBOM
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_devsecops_scan_image_clean():
    """API scan of a clean image returns pass risk and no CVEs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/agents/devsecops/scan-image",
            params={"image_name": "clean-app", "image_tag": "v2.0"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_risk"] == "pass"
    assert data["cve_findings"] == []
    assert data["zt_pillar"] == "Application"


@pytest.mark.anyio
async def test_devsecops_scan_image_vulnerable():
    """API scan of a vulnerable image returns high risk."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/agents/devsecops/scan-image",
            params={"image_name": "vulnerable-app", "image_tag": "latest"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_risk"] == "high"
    assert len(data["cve_findings"]) > 0


@pytest.mark.anyio
async def test_devsecops_scan_image_approved_base():
    """API scan passes base_image parameter and marks it approved."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/agents/devsecops/scan-image",
            params={
                "image_name": "my-app",
                "image_tag": "v1.0",
                "base_image": "registry.access.redhat.com/ubi9/ubi-minimal",
            },
        )
    assert response.status_code == 200
    assert response.json()["base_image_approved"] is True


@pytest.mark.anyio
async def test_devsecops_sbom_endpoint():
    """DevSecOps SBOM endpoint returns valid CycloneDX structure."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/agents/devsecops/sbom/my-service")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "my-service"
    assert data["sbom_format"] == "CycloneDX-1.5"
    assert data["component_count"] > 0
    assert len(data["components"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator task / report
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_orchestrator_task_manual():
    """Create an orchestrator task with manual trigger."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/orchestrator/task",
            params={"trigger": "manual", "scope": "test-scope"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "assigned_agents" in data
    assert "required_controls" in data
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_orchestrator_task_code_push_with_controls():
    """Create orchestrator task for code_push with specific controls."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/orchestrator/task",
            params={
                "trigger": "code_push",
                "scope": "api-service",
                "controls": "AC.1.001,IA.3.083",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "AC.1.001" in data["required_controls"]
    assert "IA.3.083" in data["required_controls"]


@pytest.mark.anyio
async def test_orchestrator_task_incident_trigger():
    """Create orchestrator task with incident trigger."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/orchestrator/task",
            params={"trigger": "incident", "scope": "security-event"},
        )
    assert response.status_code == 200
    assert "task_id" in response.json()


@pytest.mark.anyio
async def test_orchestrator_report():
    """Orchestrator full compliance report has expected top-level fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/orchestrator/report")
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "timestamp" in data
    assert "sprs_score" in data
    assert "zt_scorecard" in data
    assert "sprs_details" in data
    assert "agent_runs" in data


@pytest.mark.anyio
async def test_orchestrator_report_zt_scorecard_structure():
    """Each ZT scorecard entry has the expected fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/orchestrator/report")
    scorecard = response.json()["zt_scorecard"]
    assert len(scorecard) > 0
    for entry in scorecard:
        assert "pillar" in entry
        assert "total_controls" in entry
        assert "implemented" in entry
        assert "maturity_pct" in entry


# ─────────────────────────────────────────────────────────────────────────────
# Mistral agent endpoints
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_mistral_code_review_mock():
    """Code review endpoint returns analysis in mock mode (no API key)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "code_snippet": "password = 'hardcoded_secret'",
            "language": "python",
            "relevant_controls": ["AC.1.001", "IA.1.076"],
        }
        response = await ac.post("/api/agents/mistral/code-review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert "model" in data


@pytest.mark.anyio
async def test_mistral_ask_mock():
    """Q&A endpoint returns an answer string in mock mode."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "question": "What controls apply to MFA?",
            "context": "",
        }
        response = await ac.post("/api/agents/mistral/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "answer" in data
    assert data["question"] == "What controls apply to MFA?"
    if not os.getenv("MISTRAL_API_KEY"):
        assert "Mock answer" in data["answer"]


@pytest.mark.anyio
async def test_mistral_gap_analysis_with_evidence():
    """Gap analysis with existing evidence returns a structured result."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "control_id": "IA.3.083",
            "control_title": "Employ multi-factor authentication",
            "control_description": "Use MFA for all network access.",
            "zt_pillar": "User",
            "current_status": "partially_implemented",
            "existing_evidence": ["Okta MFA policy document", "FIDO2 enrollment log"],
        }
        response = await ac.post("/api/agents/mistral/gap-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["control_id"] == "IA.3.083"
    assert "analysis" in data
