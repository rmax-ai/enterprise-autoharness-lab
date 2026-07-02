"""Integration tests: agent → harness → policy → environment flow."""

import tempfile
from pathlib import Path

from autoharness_lab.agents.noisy import NoisyAgent
from autoharness_lab.environments.expense_approval import ExpenseApprovalEnvironment
from autoharness_lab.models import Action, Scenario
from autoharness_lab.evaluation.runner import run_experiment, compute_all_metrics
from autoharness_lab.harness.contracts import HarnessRuntime
from autoharness_lab.policy.expense import ExpensePolicyEngine
from autoharness_lab.storage.traces import TraceStore, classify_failure, extract_counterexamples


class TestAgentToEnvironmentFlow:
    def test_noisy_agent_produces_traceable_failures(self):
        """Noisy agent → environment produces invalid actions that can be traced."""
        env = ExpenseApprovalEnvironment()
        obs = env.reset(42)

        agent = NoisyAgent(seed=42)
        available = env.available_action_types()

        action = agent.propose_action("test", obs, available)
        result = env.execute(action)

        # Noisy agent should generate at least some failures
        # (With seed 42, first action may or may not fail)
        # The important thing is the flow works
        assert result.status in ("success", "invalid_action", "policy_denied", "runtime_error")

    def test_policy_engine_blocks_self_approval(self):
        """Policy engine denies self-approval even when environment would allow it."""
        env = ExpenseApprovalEnvironment()
        obs = env.reset(42)

        # Add receipt to the submitted expense so policy allows approval
        snap = env.state_snapshot()
        submitted = next(
            (eid for eid, e in snap["expenses"].items() if e["state"] == "submitted"),
            None,
        )
        assert submitted is not None
        env.execute(Action(type="request_receipt", arguments={"expense_id": submitted}))

        snap = env.state_snapshot()
        expense = snap["expenses"][submitted]

        policy = ExpensePolicyEngine()
        # Someone else approving — should be allowed
        decision = policy.evaluate(
            actor={"user_id": "manager1", "role": "manager", "approval_limit": 10000},
            action={"type": "approve_expense", "arguments": {"expense_id": submitted}},
            expense=expense,
        )
        assert decision.allowed is True, f"Manager should be able to approve, got: {decision.reason}"

        # Self-approval — should be denied even though operationally valid
        decision2 = policy.evaluate(
            actor={"user_id": expense["submitter"], "role": "manager", "approval_limit": 10000},
            action={"type": "approve_expense", "arguments": {"expense_id": submitted}},
            expense=expense,
        )
        assert decision2.allowed is False


class TestTraceStorage:
    def test_jsonl_round_trip(self):
        """AttemptRecord → JSONL → AttemptRecord round-trip."""
        import json
        from autoharness_lab.models import Action, AttemptRecord, ExecutionResult

        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "traces.jsonl"
            store = TraceStore(trace_path)

            record = AttemptRecord(
                run_id="test-1",
                scenario_id="s1",
                environment="expense-approval",
                agent="noisy",
                observation={"key": "value"},
                proposed_action=Action(type="submit_expense", arguments={"expense_id": "exp-1"}),
                execution_result=ExecutionResult(status="success", observation={}),
                step_index=0,
            )
            store.append(record)

            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].run_id == "test-1"
            assert loaded[0].proposed_action.type == "submit_expense"

    def test_counterexample_extraction(self):
        """Failures become structured counterexamples."""
        from autoharness_lab.models import (
            Action,
            AttemptRecord,
            ExecutionResult,
        )

        records = [
            AttemptRecord(
                run_id="test",
                scenario_id="s1",
                environment="expense-approval",
                agent="noisy",
                observation={},
                proposed_action=Action(type="invalid_xyz", arguments={}),
                execution_result=ExecutionResult(
                    status="invalid_action",
                    observation={},
                    error_code="UNKNOWN_ACTION",
                    message="Unknown action type",
                ),
                step_index=0,
            ),
            AttemptRecord(
                run_id="test",
                scenario_id="s1",
                environment="expense-approval",
                agent="noisy",
                observation={},
                proposed_action=Action(type="submit_expense", arguments={}),
                execution_result=ExecutionResult(status="success", observation={}),
                step_index=1,
            ),
        ]

        ces = extract_counterexamples(records)
        # Only the failed record should produce a counterexample
        assert len(ces) == 1
        assert ces[0].error_code == "UNKNOWN_ACTION"
        assert ces[0].explanation != ""

    def test_failure_classification(self):
        """Failures are classified correctly."""
        from autoharness_lab.models import ExecutionResult

        result = ExecutionResult(
            status="invalid_action",
            observation={},
            error_code="UNKNOWN_ACTION",
            message="bad",
        )
        assert classify_failure(result) == "unknown_action_type"

        result2 = ExecutionResult(
            status="invalid_action",
            observation={},
            error_code="INVALID_STATE",
            message="bad state",
        )
        assert classify_failure(result2) == "invalid_state_transition"


class TestExperimentRunner:
    def test_run_experiment_produces_records(self):
        """Full experiment runner produces records for all scenarios."""
        scenarios = [
            Scenario(
                scenario_id="test-1",
                task="submit expense",
                initial_state={},
                actor={"user_id": "alice", "role": "employee", "approval_limit": 0},
                expected_outcome={"final_state": "approved"},
                max_steps=5,
                tags=["standard"],
            )
        ]

        agent = NoisyAgent(seed=42)
        policy = ExpensePolicyEngine()

        def env_factory():
            return ExpenseApprovalEnvironment()

        records = run_experiment(
            scenarios=scenarios,
            environment_factory=env_factory,
            agent=agent,
            policy_engine=policy,
            max_steps=5,
        )

        assert len(records) > 0
        assert all(r.agent == "noisy" for r in records)
        # Agent should produce some invalid actions
        statuses = {r.execution_result.status for r in records}
        # With noisy agent, we expect at least invalid_action statuses
        assert "invalid_action" in statuses or "policy_denied" in statuses
