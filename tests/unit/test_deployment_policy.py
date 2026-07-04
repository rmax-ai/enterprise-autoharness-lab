"""Unit tests for the deployment policy engine."""

from autoharness_lab.policy.deployment import DeploymentPolicyEngine


class TestDeploymentPolicyEngine:
    def test_allows_manager_approve_other(self):
        engine = DeploymentPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "approve_deployment",
                "arguments": {"deployment_id": "dep-1", "approver": "manager_alex"},
            },
            deployment={
                "state": "created",
                "creator": "bob",
                "checks_passed": True,
            },
        )
        assert result.allowed is True

    def test_blocks_self_approval(self):
        engine = DeploymentPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "bob", "role": "developer"},
            action={
                "type": "approve_deployment",
                "arguments": {"deployment_id": "dep-1", "approver": "bob"},
            },
            deployment={
                "state": "created",
                "creator": "bob",
                "checks_passed": True,
            },
        )
        assert result.allowed is False
        assert result.rule_id == "DEPLOY-001"

    def test_blocks_approve_without_checks(self):
        engine = DeploymentPolicyEngine(require_checks=True)
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "approve_deployment",
                "arguments": {"deployment_id": "dep-1"},
            },
            deployment={
                "state": "created",
                "creator": "bob",
                "checks_passed": False,
            },
        )
        assert result.allowed is False
        assert result.rule_id == "DEPLOY-003"

    def test_blocks_start_unapproved(self):
        engine = DeploymentPolicyEngine(require_approval=True)
        result = engine.evaluate(
            actor={"user_id": "alice", "role": "developer"},
            action={
                "type": "start_deployment",
                "arguments": {"deployment_id": "dep-1"},
            },
            deployment={"state": "created", "environment": "staging"},
        )
        assert result.allowed is False
        assert result.rule_id == "DEPLOY-006"

    def test_allows_start_approved(self):
        engine = DeploymentPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "alice", "role": "developer"},
            action={
                "type": "start_deployment",
                "arguments": {"deployment_id": "dep-1"},
            },
            deployment={"state": "approved", "environment": "staging"},
        )
        assert result.allowed is True

    def test_blocks_cancel_completed(self):
        engine = DeploymentPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "alice", "role": "developer"},
            action={
                "type": "cancel_deployment",
                "arguments": {"deployment_id": "dep-1"},
            },
            deployment={"state": "completed"},
        )
        assert result.allowed is False
        assert result.rule_id == "DEPLOY-005"

    def test_blocks_developer_rollback_production(self):
        engine = DeploymentPolicyEngine(require_manager_for_rollback=True)
        result = engine.evaluate(
            actor={"user_id": "alice", "role": "developer"},
            action={
                "type": "rollback_deployment",
                "arguments": {"deployment_id": "dep-1"},
            },
            deployment={
                "state": "started",
                "environment": "production",
            },
        )
        assert result.allowed is False
        assert result.rule_id == "DEPLOY-004"

    def test_allows_manager_rollback_production(self):
        engine = DeploymentPolicyEngine(require_manager_for_rollback=True)
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "rollback_deployment",
                "arguments": {"deployment_id": "dep-1"},
            },
            deployment={
                "state": "started",
                "environment": "production",
            },
        )
        assert result.allowed is True

    def test_allows_developer_rollback_staging(self):
        engine = DeploymentPolicyEngine(require_manager_for_rollback=True)
        result = engine.evaluate(
            actor={"user_id": "alice", "role": "developer"},
            action={
                "type": "rollback_deployment",
                "arguments": {"deployment_id": "dep-1"},
            },
            deployment={
                "state": "started",
                "environment": "staging",
            },
        )
        assert result.allowed is True

    def test_allows_create_deployment(self):
        engine = DeploymentPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "alice", "role": "developer"},
            action={
                "type": "create_deployment",
                "arguments": {"service": "test", "environment": "staging"},
            },
            deployment=None,
        )
        assert result.allowed is True
