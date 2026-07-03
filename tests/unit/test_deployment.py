"""Tests for deployment environment and policy."""

import pytest

from autoharness_lab.environments.deployment import (
    DeploymentEnvironment,
)
from autoharness_lab.models import Action
from autoharness_lab.policy.deployment import DeploymentPolicyEngine


@pytest.fixture
def env():
    e = DeploymentEnvironment()
    e.reset(42)
    return e


class TestDeploymentEnvironment:
    def test_name(self, env):
        assert env.name == "deployment"

    def test_reset_creates_deployments(self, env):
        snap = env.state_snapshot()
        assert len(snap["deployments"]) == 3

    def test_available_actions(self, env):
        actions = env.available_action_types()
        assert "create_deployment" in actions
        assert "approve_deployment" in actions
        assert "rollback_deployment" in actions

    def test_create_deployment(self, env):
        result = env.execute(
            Action(
                type="create_deployment",
                arguments={
                    "service": "test-svc",
                    "version": "v1.0",
                    "environment": "staging",
                    "requester": "dev_test",
                },
            )
        )
        assert result.status == "success"

    def test_create_missing_fields(self, env):
        result = env.execute(Action(type="create_deployment", arguments={"service": "test"}))
        assert result.status == "invalid_action"

    def test_approve_draft(self, env):
        result = env.execute(
            Action(
                type="approve_deployment",
                arguments={
                    "deployment_id": "dep-0042",
                    "approver": "manager_carol",
                },
            )
        )
        assert result.status == "success"

    def test_self_approval_blocked(self, env):
        result = env.execute(
            Action(
                type="approve_deployment",
                arguments={"deployment_id": "dep-0042", "approver": "dev_alex"},
            )
        )
        assert result.status == "invalid_action"
        assert result.error_code == "SELF_APPROVAL"

    def test_start_approved(self, env):
        # dep-0044 is already approved by reset
        result = env.execute(
            Action(
                type="start_deployment",
                arguments={"deployment_id": "dep-0044"},
            )
        )
        assert result.status == "success"

    def test_unknown_action(self, env):
        result = env.execute(Action(type="deploy_to_mars", arguments={}))
        assert result.status == "invalid_action"

    def test_state_snapshot(self, env):
        snap = env.state_snapshot()
        assert "deployments" in snap
        assert "config" in snap


class TestDeploymentPolicy:
    def test_manager_can_approve(self):
        eng = DeploymentPolicyEngine()
        result = eng.evaluate(
            {"user_id": "manager_carol", "role": "manager"},
            {"type": "approve_deployment", "arguments": {}},
            {"requester": "dev_alex", "risk_level": "low"},
        )
        assert result.allowed

    def test_self_approval_denied(self):
        eng = DeploymentPolicyEngine()
        result = eng.evaluate(
            {"user_id": "dev_alex", "role": "developer"},
            {"type": "approve_deployment", "arguments": {}},
            {"requester": "dev_alex"},
        )
        assert not result.allowed
        assert result.rule_id == "DEP-001"

    def test_high_risk_needs_manager(self):
        eng = DeploymentPolicyEngine()
        result = eng.evaluate(
            {"user_id": "dev_alex", "role": "developer"},
            {"type": "start_deployment", "arguments": {}},
            {"risk_level": "high"},
        )
        assert not result.allowed
        assert result.rule_id == "DEP-002"

    def test_production_freeze(self):
        eng = DeploymentPolicyEngine(production_freeze=True)
        result = eng.evaluate(
            {"user_id": "manager_carol", "role": "manager"},
            {"type": "start_deployment", "arguments": {}},
            {"environment": "production"},
        )
        assert not result.allowed
        assert result.rule_id == "DEP-003"

    def test_prod_rollback_needs_manager(self):
        eng = DeploymentPolicyEngine()
        result = eng.evaluate(
            {"user_id": "dev_alex", "role": "developer"},
            {"type": "rollback_deployment", "arguments": {}},
            {"environment": "production"},
        )
        assert not result.allowed
        assert result.rule_id == "DEP-004"
