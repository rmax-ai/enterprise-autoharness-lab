"""Unit tests for core models."""

import pytest
from pydantic import ValidationError

from autoharness_lab.models import (
    Action,
    AttemptRecord,
    Counterexample,
    ExecutionResult,
    HarnessDecision,
    PolicyDecision,
    Scenario,
)


class TestAction:
    def test_valid_action(self):
        a = Action(type="submit_expense", arguments={"expense_id": "exp-1"})
        assert a.type == "submit_expense"
        assert a.arguments["expense_id"] == "exp-1"

    def test_default_arguments(self):
        a = Action(type="test")
        assert a.arguments == {}

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            Action(type="test", extra_field="nope")

    def test_frozen(self):
        a = Action(type="test")
        with pytest.raises(ValidationError):
            a.type = "changed"  # type: ignore[misc]


class TestExecutionResult:
    def test_success_result(self):
        r = ExecutionResult(
            status="success",
            observation={"key": "value"},
        )
        assert r.status == "success"
        assert r.reward == 0.0

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            ExecutionResult(status="not_a_status", observation={})


class TestHarnessDecision:
    def test_accepted_with_normalized(self):
        d = HarnessDecision(
            accepted=True,
            normalized_action=Action(type="submit_expense", arguments={"expense_id": "exp-1"}),
            reason="valid",
        )
        assert d.accepted
        assert d.normalized_action is not None

    def test_rejected_no_normalized(self):
        d = HarnessDecision(accepted=False, reason="unknown action")
        assert not d.accepted
        assert d.normalized_action is None


class TestPolicyDecision:
    def test_allowed(self):
        d = PolicyDecision(allowed=True, rule_id="R1", reason="ok")
        assert d.allowed

    def test_denied(self):
        d = PolicyDecision(allowed=False, rule_id="EXP-001", reason="self-approval")
        assert not d.allowed


class TestCounterexample:
    def test_from_failure(self):
        ce = Counterexample(
            observation={"expenses": {}},
            proposed_action=Action(type="invalid", arguments={}),
            expected_classification="rejected",
            actual_result=ExecutionResult(
                status="invalid_action",
                observation={},
                error_code="UNKNOWN_ACTION",
                message="bad",
            ),
            error_code="UNKNOWN_ACTION",
            explanation="Unknown action type",
        )
        assert ce.error_code == "UNKNOWN_ACTION"


class TestScenario:
    def test_valid_scenario(self):
        s = Scenario(
            scenario_id="test-1",
            task="do something",
            initial_state={},
            actor={"user_id": "alice"},
            expected_outcome={"final_state": "approved"},
            max_steps=10,
            tags=["standard"],
        )
        assert s.scenario_id == "test-1"
        assert s.max_steps == 10
