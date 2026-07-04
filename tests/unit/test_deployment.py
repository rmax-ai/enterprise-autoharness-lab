"""Unit tests for the deployment environment."""

from autoharness_lab.environments.deployment import (
    DeploymentEnvironment,
    DeploymentState,
)
from autoharness_lab.models import Action


class TestDeploymentEnvironment:
    def test_name(self):
        env = DeploymentEnvironment()
        assert env.name == "deployment"

    def test_reset_creates_deployments(self):
        env = DeploymentEnvironment()
        obs = env.reset(42)
        assert "deployments" in obs
        deps = obs["deployments"]
        assert len(deps) == 3
        dep = deps["dep-0042"]
        assert dep["state"] == "draft"
        assert dep["service"] == "payments-api"

    def test_available_action_types(self):
        env = DeploymentEnvironment()
        actions = env.available_action_types()
        assert "create_deployment" in actions
        assert "approve_deployment" in actions
        assert "start_deployment" in actions
        assert "cancel_deployment" in actions
        assert "rollback_deployment" in actions

    def test_create_deployment(self):
        env = DeploymentEnvironment()
        env.reset(100)
        action = Action(
            type="create_deployment",
            arguments={
                "deployment_id": "dep-new",
                "service": "test-svc",
                "version": "v1.0",
                "environment": "staging",
                "creator": "alice",
            },
        )
        result = env.execute(action)
        assert result.status == "success"
        assert result.reward == 0.1
        assert "dep-new" in env._deployments
        assert env._deployments["dep-new"].state == DeploymentState.CREATED

    def test_create_invalid_environment(self):
        env = DeploymentEnvironment()
        env.reset(100)
        action = Action(
            type="create_deployment",
            arguments={
                "service": "test-svc",
                "environment": "mars",
            },
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "INVALID_ENVIRONMENT"

    def test_unknown_action(self):
        env = DeploymentEnvironment()
        env.reset(100)
        action = Action(type="invalid_action", arguments={})
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "UNKNOWN_ACTION"

    def test_approve_created_with_checks(self):
        env = DeploymentEnvironment()
        env.reset(100)
        # dep-0101 is already in "created" state with checks_passed
        action = Action(
            type="approve_deployment",
            arguments={"deployment_id": "dep-0101", "approver": "manager_alex"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert env._deployments["dep-0101"].state == DeploymentState.APPROVED
        assert env._deployments["dep-0101"].approver == "manager_alex"

    def test_approve_without_checks(self):
        env = DeploymentEnvironment()
        env.reset(100)
        # dep-0100 is draft, no checks. Create a deployment without checks
        env._deployments["dep-test"] = type(env._deployments["dep-0100"])(
            deployment_id="dep-test",
            service="test",
            version="v1",
            environment="staging",
            creator="alice",
            state=DeploymentState.CREATED,
            checks_passed=False,
        )
        action = Action(
            type="approve_deployment",
            arguments={"deployment_id": "dep-test", "approver": "manager_alex"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "CHECKS_NOT_PASSED"

    def test_start_approved_deployment(self):
        env = DeploymentEnvironment()
        env.reset(100)
        # Create a staging deployment, approve, then start
        env._deployments["dep-staging"] = type(env._deployments["dep-0100"])(
            deployment_id="dep-staging",
            service="test-svc",
            version="v1",
            environment="staging",
            creator="alice",
            state=DeploymentState.APPROVED,
            checks_passed=True,
        )
        action = Action(
            type="start_deployment",
            arguments={"deployment_id": "dep-staging"},
        )
        result = env.execute(action)
        assert result.status == "success"
        # Staging auto-completes
        assert env._deployments["dep-staging"].state == DeploymentState.COMPLETED

    def test_cancel_created_deployment(self):
        env = DeploymentEnvironment()
        env.reset(100)
        # dep-0100 is draft, dep-0101 is created with checks
        # Create one without checks
        env._deployments["dep-cancel"] = type(env._deployments["dep-0100"])(
            deployment_id="dep-cancel",
            service="test",
            version="v1",
            environment="staging",
            creator="alice",
            state=DeploymentState.CREATED,
            checks_passed=False,
        )
        action = Action(
            type="cancel_deployment",
            arguments={"deployment_id": "dep-cancel"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert env._deployments["dep-cancel"].state == DeploymentState.CANCELLED

    def test_cannot_cancel_completed(self):
        env = DeploymentEnvironment()
        env.reset(100)
        env._deployments["dep-done"] = type(env._deployments["dep-0100"])(
            deployment_id="dep-done",
            service="test",
            version="v1",
            environment="staging",
            creator="alice",
            state=DeploymentState.COMPLETED,
            checks_passed=True,
        )
        action = Action(
            type="cancel_deployment",
            arguments={"deployment_id": "dep-done"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"

    def test_rollback_started_deployment(self):
        env = DeploymentEnvironment()
        env.reset(100)
        env._deployments["dep-rb"] = type(env._deployments["dep-0100"])(
            deployment_id="dep-rb",
            service="test",
            version="v1",
            environment="staging",
            creator="alice",
            state=DeploymentState.STARTED,
            checks_passed=True,
        )
        action = Action(
            type="rollback_deployment",
            arguments={"deployment_id": "dep-rb"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert env._deployments["dep-rb"].state == DeploymentState.ROLLED_BACK

    def test_cannot_rollback_draft(self):
        env = DeploymentEnvironment()
        env.reset(100)
        action = Action(
            type="rollback_deployment",
            arguments={"deployment_id": "dep-0100"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"

    def test_missing_deployment_id(self):
        env = DeploymentEnvironment()
        env.reset(100)
        action = Action(
            type="approve_deployment",
            arguments={"approver": "manager_alex"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "MISSING_DEPLOYMENT_ID"
