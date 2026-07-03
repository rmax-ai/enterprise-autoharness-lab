"""Tests for harness artifact registry."""

import tempfile
from pathlib import Path

from autoharness_lab.harness.registry import HarnessRegistry

VALID_CODE = """
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
"""


class TestHarnessRegistry:
    def test_store_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            artifact = registry.store(
                environment="expense-approval",
                code=VALID_CODE,
                model_name="mock",
                generation_prompt_hash="abc123",
            )
            assert artifact.environment == "expense-approval"
            assert artifact.version == 0
            assert artifact.code == VALID_CODE
            assert artifact.lifecycle_state == "GENERATED"

            loaded = registry.load(artifact.harness_id)
            assert loaded is not None
            assert loaded.code.strip() == VALID_CODE.strip()

    def test_version_increments(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            a1 = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            a2 = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            assert a1.version == 0
            assert a2.version == 1

    def test_list_by_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            registry.store("expense-approval", VALID_CODE, "mock", "h1")
            registry.store("support-ticket", VALID_CODE, "mock", "h2")

            expense = registry.list_versions("expense-approval")
            support = registry.list_versions("support-ticket")
            assert len(expense) == 1
            assert len(support) == 1

    def test_get_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            registry.store("expense-approval", VALID_CODE, "mock", "h1")
            a2 = registry.store("expense-approval", VALID_CODE, "mock", "h1")

            latest = registry.get_latest("expense-approval")
            assert latest is not None
            assert latest.harness_id == a2.harness_id

    def test_set_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            a0 = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            a1 = registry.store("expense-approval", VALID_CODE, "mock", "h1")

            registry.set_active(a0.harness_id)
            active = registry.get_active("expense-approval")
            assert active is not None
            assert active.harness_id == a0.harness_id

            loaded = registry.load(a0.harness_id)
            assert loaded is not None
            assert loaded.lifecycle_state == "ACTIVE"

    def test_get_active_returns_none_when_none_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            registry.store("expense-approval", VALID_CODE, "mock", "h1")
            assert registry.get_active("expense-approval") is None

    def test_code_hash_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            a1 = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            a2 = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            assert a1.code_hash == a2.code_hash

    def test_parent_tracking(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            parent = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            child = registry.store(
                "expense-approval",
                VALID_CODE,
                "mock",
                "h1",
                parent_harness_id=parent.harness_id,
            )
            assert child.parent_harness_id == parent.harness_id

    def test_directory_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            a = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            harness_dir = Path(tmp) / "expense-approval" / f"v{a.version}"
            assert harness_dir.exists()
            assert (harness_dir / "harness.py").exists()
            assert (harness_dir / "metadata.json").exists()

    def test_update_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            a = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            registry.update_metrics(a.harness_id, {"composite_score": 0.85})

            loaded = registry.load(a.harness_id)
            assert loaded is not None
            assert loaded.evaluation_metrics["composite_score"] == 0.85
