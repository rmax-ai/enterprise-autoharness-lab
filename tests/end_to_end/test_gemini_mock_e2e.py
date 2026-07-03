"""End-to-end test: GeminiAgent with mock client in full experiment flow."""

from __future__ import annotations

from unittest.mock import MagicMock

from autoharness_lab.agents.gemini import ActionResponse, GeminiAgent
from autoharness_lab.environments.expense_approval import ExpenseApprovalEnvironment
from autoharness_lab.evaluation.runner import compute_all_metrics, run_experiment
from autoharness_lab.models import Scenario
from autoharness_lab.policy.expense import ExpensePolicyEngine


class TestGeminiMockE2E:
    """Full experiment pipeline with mocked Gemini agent."""

    def test_mocked_gemini_completes_experiment(self):
        """GeminiAgent with mock client produces records in runner."""
        mock_client = MagicMock()
        mock_client.generate_structured.side_effect = [
            ActionResponse(type="request_receipt", arguments={"expense_id": "exp-0001"}),
            ActionResponse(type="submit_expense", arguments={"expense_id": "exp-0001"}),
            ActionResponse(
                type="approve_expense",
                arguments={"expense_id": "exp-0001", "actor": "manager1"},
            ),
        ]

        agent = GeminiAgent(client=mock_client)
        scenarios = [
            Scenario(
                scenario_id="mock-e2e-1",
                task="alice_submit_office_supplies",
                initial_state={},
                actor={"user_id": "alice", "role": "employee", "approval_limit": 0},
                expected_outcome={"final_state": "approved"},
                max_steps=5,
                tags=["standard"],
            )
        ]
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
        assert all(record.agent == "gemini" for record in records)

        metrics = compute_all_metrics(records)
        assert "task_success_rate" in metrics
