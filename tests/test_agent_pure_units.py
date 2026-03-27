"""
Pure Unit Tests for Agent Business Logic
No database or HTTP — tests agent class methods directly.

Covers:
  - ICAMAgent.check_mfa_coverage()
  - ICAMAgent.check_least_privilege()
  - DevSecOpsAgent.scan_container_image()
  - DevSecOpsAgent.generate_sbom()
  - DevSecOpsAgent.evaluate_pipeline_gates()
  - ComplianceOrchestrator.create_task() routing logic
"""
import uuid
from datetime import datetime, timedelta, UTC


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_user(uid, name, mfa_enabled, mfa_type, privileged,
               last_login_days=1, review_days=30, no_review=False):
    from agents.icam_agent.agent import UserRecord
    return UserRecord(
        user_id=uid,
        username=name,
        roles=["Admin" if privileged else "User"],
        mfa_enabled=mfa_enabled,
        mfa_type=mfa_type,
        last_login=datetime.now(UTC) - timedelta(days=last_login_days),
        account_status="active",
        privileged=privileged,
        department="IT",
        last_access_review=(None if no_review
                            else datetime.now(UTC) - timedelta(days=review_days)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ICAMAgent – MFA coverage
# ─────────────────────────────────────────────────────────────────────────────

class TestICAMAgentMFACoverage:
    """Unit tests for ICAMAgent.check_mfa_coverage()."""

    def test_all_mfa_enabled_returns_implemented(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=False)
        agent.users = [
            _make_user("u1", "alice", True, "fido2", True),
            _make_user("u2", "bob", True, "totp", False),
        ]
        result = agent.check_mfa_coverage()
        assert result.control_id == "IA.3.083"
        assert result.status == "implemented"
        assert result.confidence >= 0.95
        assert result.findings == []

    def test_no_mfa_enabled_returns_not_implemented(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=False)
        agent.users = [
            _make_user("u1", "alice", False, "none", True),
            _make_user("u2", "bob", False, "none", False),
        ]
        result = agent.check_mfa_coverage()
        assert result.status == "not_implemented"
        assert result.confidence < 0.5
        assert len(result.findings) > 0
        assert len(result.remediation) > 0

    def test_partial_mfa_coverage(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=False)
        agent.users = [
            _make_user("u1", "alice", True, "fido2", True),
            _make_user("u2", "bob", False, "none", False),
        ]
        result = agent.check_mfa_coverage()
        assert result.status in ("partially_implemented", "not_implemented")
        assert len(result.findings) > 0

    def test_privileged_without_mfa_flagged(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=False)
        agent.users = [_make_user("u1", "priv.no.mfa", False, "none", True)]
        result = agent.check_mfa_coverage()
        assert len(result.findings) > 0

    def test_evidence_id_is_valid_uuid(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=True)
        result = agent.check_mfa_coverage()
        uuid.UUID(result.evidence_id)  # raises ValueError if invalid

    def test_mock_users_count(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=True)
        assert len(agent.users) == 4

    def test_confidence_in_range(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=True)
        result = agent.check_mfa_coverage()
        assert 0.0 <= result.confidence <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# ICAMAgent – least privilege
# ─────────────────────────────────────────────────────────────────────────────

class TestICAMAgentLeastPrivilege:
    """Unit tests for ICAMAgent.check_least_privilege()."""

    def test_clean_accounts_returns_implemented(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=False)
        agent.users = [_make_user("u1", "active.user", True, "totp", False,
                                  last_login_days=5, review_days=30)]
        result = agent.check_least_privilege()
        assert result.control_id == "AC.2.007"
        assert result.status == "implemented"
        assert result.confidence >= 0.9
        assert result.findings == []

    def test_stale_accounts_lowers_confidence(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=False)
        agent.users = [_make_user("u1", "stale.user", True, "totp", False,
                                  last_login_days=200, review_days=400)]
        result = agent.check_least_privilege()
        assert result.status in ("partially_implemented", "not_implemented")
        assert len(result.findings) > 0
        assert len(result.remediation) > 0

    def test_unreviewed_accounts_flagged(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=False)
        agent.users = [_make_user("u1", "unreviewed", True, "totp", False,
                                  last_login_days=5, no_review=True)]
        result = agent.check_least_privilege()
        assert len(result.findings) > 0
        findings_text = " ".join(result.findings).lower()
        assert "review" in findings_text or "overdue" in findings_text

    def test_evidence_id_is_valid_uuid(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=True)
        result = agent.check_least_privilege()
        uuid.UUID(result.evidence_id)

    def test_confidence_in_range(self):
        from agents.icam_agent.agent import ICAMAgent
        agent = ICAMAgent(mock_mode=True)
        result = agent.check_least_privilege()
        assert 0.0 <= result.confidence <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# DevSecOpsAgent – scan_container_image
# ─────────────────────────────────────────────────────────────────────────────

class TestDevSecOpsAgentScan:
    """Unit tests for DevSecOpsAgent.scan_container_image()."""

    def _agent(self):
        from agents.devsecops_agent.agent import DevSecOpsAgent
        return DevSecOpsAgent(mock_mode=True)

    def test_clean_image_passes(self):
        result = self._agent().scan_container_image("my-clean-app", "v1.0")
        assert result["overall_risk"] == "pass"
        assert result["cve_findings"] == []
        assert result["high_count"] == 0
        assert result["critical_count"] == 0

    def test_vulnerable_image_flagged(self):
        result = self._agent().scan_container_image("vulnerable-service", "latest")
        assert result["overall_risk"] == "high"
        assert len(result["cve_findings"]) > 0
        assert result["high_count"] > 0

    def test_approved_base_image(self):
        result = self._agent().scan_container_image(
            "myapp", "v1.0",
            base_image="registry.access.redhat.com/ubi9/ubi-minimal",
        )
        assert result["base_image_approved"] is True

    def test_unapproved_base_image(self):
        result = self._agent().scan_container_image(
            "myapp", "v1.0",
            base_image="docker.io/ubuntu:22.04",
        )
        assert result["base_image_approved"] is False

    def test_no_base_image(self):
        result = self._agent().scan_container_image("myapp", "v1.0")
        assert result["base_image"] is None

    def test_evidence_id_is_uuid(self):
        result = self._agent().scan_container_image("myapp", "v1.0")
        uuid.UUID(result["evidence_id"])

    def test_zt_pillar_is_application(self):
        result = self._agent().scan_container_image("myapp", "v1.0")
        assert result["zt_pillar"] == "Application"

    def test_cmmc_controls_non_empty(self):
        result = self._agent().scan_container_image("myapp", "v1.0")
        assert len(result["cmmc_controls"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# DevSecOpsAgent – generate_sbom
# ─────────────────────────────────────────────────────────────────────────────

class TestDevSecOpsAgentSBOM:
    """Unit tests for DevSecOpsAgent.generate_sbom()."""

    def _agent(self):
        from agents.devsecops_agent.agent import DevSecOpsAgent
        return DevSecOpsAgent()

    def test_sbom_format(self):
        result = self._agent().generate_sbom("test-svc")
        assert result["sbom_format"] == "CycloneDX-1.5"

    def test_sbom_service_name(self):
        result = self._agent().generate_sbom("my-api")
        assert result["service"] == "my-api"

    def test_sbom_has_components(self):
        result = self._agent().generate_sbom("test-svc")
        assert result["component_count"] > 0
        assert len(result["components"]) == result["component_count"]

    def test_sbom_zt_pillar(self):
        result = self._agent().generate_sbom("test-svc")
        assert result["zt_pillar"] == "Application"

    def test_sbom_evidence_uuid(self):
        result = self._agent().generate_sbom("test-svc")
        uuid.UUID(result["evidence_id"])


# ─────────────────────────────────────────────────────────────────────────────
# DevSecOpsAgent – evaluate_pipeline_gates
# ─────────────────────────────────────────────────────────────────────────────

class TestDevSecOpsAgentPipelineGates:
    """Unit tests for DevSecOpsAgent.evaluate_pipeline_gates()."""

    def _agent(self):
        from agents.devsecops_agent.agent import DevSecOpsAgent
        return DevSecOpsAgent()

    def test_pipeline_structure(self):
        result = self._agent().evaluate_pipeline_gates("test-pipeline")
        assert result["pipeline_id"] == "test-pipeline"
        assert "gates_total" in result
        assert "gates_passed" in result
        assert "gates_failed" in result
        assert "gate_details" in result

    def test_confidence_range(self):
        result = self._agent().evaluate_pipeline_gates("test-pipeline")
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_image_signing_fails(self):
        """The mock pipeline always has image_signing as a failing gate."""
        result = self._agent().evaluate_pipeline_gates("any-pipeline")
        assert "image_signing" in result["failed_gates"]
        assert result["overall_status"] == "fail"

    def test_gates_counts_consistent(self):
        result = self._agent().evaluate_pipeline_gates("test-pipeline")
        # Passed + failed + warned should account for all gates
        assert result["gates_passed"] + result["gates_failed"] <= result["gates_total"]


# ─────────────────────────────────────────────────────────────────────────────
# ComplianceOrchestrator – task routing
# ─────────────────────────────────────────────────────────────────────────────

class TestComplianceOrchestrator:
    """Unit tests for ComplianceOrchestrator task creation and routing."""

    def _orch(self):
        from agents.orchestrator.agent import ComplianceOrchestrator
        return ComplianceOrchestrator()

    def test_code_push_assigns_devsecops_and_icam(self):
        from agents.orchestrator.agent import TaskTrigger, AgentType
        task = self._orch().create_task(trigger=TaskTrigger.CODE_PUSH, scope="api")
        assert AgentType.DEVSECOPS in task.assigned_agents
        assert AgentType.ICAM in task.assigned_agents

    def test_code_push_sets_default_controls(self):
        from agents.orchestrator.agent import TaskTrigger
        task = self._orch().create_task(trigger=TaskTrigger.CODE_PUSH, scope="api")
        assert len(task.required_controls) > 0

    def test_incident_assigns_ops_and_mistral(self):
        from agents.orchestrator.agent import TaskTrigger, AgentType
        task = self._orch().create_task(trigger=TaskTrigger.INCIDENT, scope="breach")
        assert AgentType.OPS in task.assigned_agents
        assert AgentType.MISTRAL in task.assigned_agents

    def test_assessment_assigns_all_agents(self):
        from agents.orchestrator.agent import TaskTrigger, AgentType
        task = self._orch().create_task(trigger=TaskTrigger.ASSESSMENT, scope="full")
        assert len(task.assigned_agents) == len(list(AgentType))

    def test_manual_assigns_governance(self):
        from agents.orchestrator.agent import TaskTrigger, AgentType
        task = self._orch().create_task(trigger=TaskTrigger.MANUAL, scope="manual")
        assert AgentType.GOVERNANCE in task.assigned_agents

    def test_custom_controls_preserved(self):
        from agents.orchestrator.agent import TaskTrigger
        task = self._orch().create_task(
            trigger=TaskTrigger.MANUAL,
            scope="custom",
            required_controls=["AC.1.001", "IA.3.083"],
        )
        assert "AC.1.001" in task.required_controls
        assert "IA.3.083" in task.required_controls

    def test_tasks_queued(self):
        from agents.orchestrator.agent import TaskTrigger
        orch = self._orch()
        orch.create_task(trigger=TaskTrigger.MANUAL, scope="s1")
        orch.create_task(trigger=TaskTrigger.MANUAL, scope="s2")
        assert len(orch.task_queue) == 2

    def test_task_initial_status_pending(self):
        from agents.orchestrator.agent import TaskTrigger
        task = self._orch().create_task(trigger=TaskTrigger.MANUAL, scope="check")
        assert task.status == "pending"

    def test_task_id_is_uuid(self):
        from agents.orchestrator.agent import TaskTrigger
        task = self._orch().create_task(trigger=TaskTrigger.MANUAL, scope="check")
        uuid.UUID(task.id)
