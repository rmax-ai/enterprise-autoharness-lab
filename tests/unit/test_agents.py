"""Unit tests for agent implementations."""

from autoharness_lab.agents.noisy import NoisyAgent
from autoharness_lab.agents.scripted import ScriptedAgent


class TestScriptedAgent:
    def test_name(self):
        agent = ScriptedAgent()
        assert agent.name == "scripted"

    def test_proposes_submit_for_draft(self):
        agent = ScriptedAgent()
        obs = {
            "expenses": {
                "exp-1": {
                    "expense_id": "exp-1",
                    "amount": 30,  # Below receipt threshold
                    "state": "draft",
                    "has_receipt": False,
                    "submitter": "alice",
                }
            }
        }
        action = agent.propose_action("test", obs, ["submit_expense", "approve_expense"])
        assert action.type == "submit_expense"
        assert action.arguments["expense_id"] == "exp-1"

    def test_requests_receipt_when_needed(self):
        agent = ScriptedAgent()
        obs = {
            "expenses": {
                "exp-1": {
                    "expense_id": "exp-1",
                    "amount": 200,  # Above receipt threshold
                    "state": "draft",
                    "has_receipt": False,
                    "submitter": "alice",
                }
            }
        }
        action = agent.propose_action("test", obs, ["submit_expense", "request_receipt"])
        assert action.type == "request_receipt"

    def test_proposes_approve_for_submitted(self):
        agent = ScriptedAgent()
        obs = {
            "expenses": {
                "exp-1": {
                    "expense_id": "exp-1",
                    "amount": 100,
                    "state": "submitted",
                    "has_receipt": True,
                    "submitter": "alice",
                }
            }
        }
        action = agent.propose_action("test", obs, ["submit_expense", "approve_expense"])
        assert action.type == "approve_expense"

    def test_avoids_self_approval(self):
        agent = ScriptedAgent()
        obs = {
            "expenses": {
                "exp-1": {
                    "expense_id": "exp-1",
                    "amount": 100,
                    "state": "submitted",
                    "has_receipt": True,
                    "submitter": "scripted",  # Same as agent name
                }
            }
        }
        action = agent.propose_action("test", obs, ["submit_expense", "approve_expense"])
        assert action.type != "approve_expense"


class TestNoisyAgent:
    def test_name(self):
        agent = NoisyAgent(seed=42)
        assert agent.name == "noisy"

    def test_produces_valid_actions_sometimes(self):
        agent = NoisyAgent(seed=42)
        obs = {
            "expenses": {
                "exp-1": {
                    "expense_id": "exp-1",
                    "amount": 30,
                    "state": "draft",
                    "has_receipt": True,
                    "submitter": "alice",
                }
            }
        }
        # With fixed seed, the agent should produce consistent output
        action = agent.propose_action("test", obs, ["submit_expense", "approve_expense"])
        # Should be a valid action type
        assert action.type in ("submit_expense", "approve_expense", "request_receipt")

    def test_produces_wrong_action_types(self):
        """At 100% wrong_type_rate, always produces invalid type."""
        agent = NoisyAgent(seed=42, wrong_type_rate=1.0)
        obs = {"expenses": {}}
        action = agent.propose_action("test", obs, ["submit_expense"])
        assert action.type == "invalid_action_type_xyz"

    def test_produces_missing_fields(self):
        """At 100% missing_fields_rate, always misses fields."""
        agent = NoisyAgent(seed=42, missing_fields_rate=1.0, wrong_type_rate=0.0)
        obs = {
            "expenses": {
                "exp-1": {
                    "expense_id": "exp-1",
                    "amount": 30,
                    "state": "draft",
                    "has_receipt": True,
                    "submitter": "alice",
                }
            }
        }
        action = agent.propose_action("test", obs, ["submit_expense"])
        assert action.type == "submit_expense"
        assert action.arguments == {}  # Missing expense_id

    def test_deterministic_with_seed(self):
        """Same seed produces same sequence."""
        obs = {
            "expenses": {
                "exp-1": {
                    "expense_id": "exp-1",
                    "amount": 30,
                    "state": "draft",
                    "has_receipt": True,
                    "submitter": "alice",
                }
            }
        }
        a1 = NoisyAgent(seed=42)
        a2 = NoisyAgent(seed=42)
        action1 = a1.propose_action("test", obs, ["submit_expense"])
        action2 = a2.propose_action("test", obs, ["submit_expense"])
        assert action1.type == action2.type
        assert action1.arguments == action2.arguments
