"""File-system harness artifact registry.

Stores harness versions as directories with code + metadata files.
Zero dependencies, human-inspectable, appropriate for research prototype.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from autoharness_lab.models import HarnessArtifact


class HarnessRegistry:
    """File-system registry for harness artifact versioning.

    Layout:
        <root>/
            <environment>/
                v0/
                    harness.py      # Actual harness code
                    metadata.json   # HarnessArtifact as JSON
                v1/
                    ...
                active -> v1/       # Symlink to active version
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        environment: str,
        code: str,
        model_name: str,
        generation_prompt_hash: str,
        parent_harness_id: str | None = None,
    ) -> HarnessArtifact:
        """Store a new harness version.

        Args:
            environment: Environment name (e.g., 'expense-approval').
            code: Harness source code.
            model_name: Model that generated this harness.
            generation_prompt_hash: Hash of the prompt used.
            parent_harness_id: ID of the harness this was refined from.

        Returns:
            HarnessArtifact with assigned version and metadata.
        """
        env_dir = self._root / environment
        env_dir.mkdir(parents=True, exist_ok=True)

        existing = sorted(
            [d for d in env_dir.iterdir() if d.is_dir() and d.name.startswith("v")],
            key=lambda d: int(d.name[1:]),
        )
        version = len(existing)

        harness_id = f"harness-{environment}-v{version}-{uuid.uuid4().hex[:8]}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        version_dir = env_dir / f"v{version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        (version_dir / "harness.py").write_text(code)

        artifact = HarnessArtifact(
            harness_id=harness_id,
            environment=environment,
            version=version,
            lifecycle_state="GENERATED",
            code=code,
            code_hash=code_hash,
            parent_harness_id=parent_harness_id,
            model_name=model_name,
            generation_prompt_hash=generation_prompt_hash,
            created_at=datetime.now(UTC).isoformat(),
            static_validation={},
            evaluation_metrics={},
            approved_by=None,
        )

        (version_dir / "metadata.json").write_text(artifact.model_dump_json(indent=2))
        return artifact

    def load(self, harness_id: str) -> HarnessArtifact | None:
        """Load a harness artifact by ID."""
        for env_dir in self._root.iterdir():
            if not env_dir.is_dir():
                continue
            for version_dir in env_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                meta_path = version_dir / "metadata.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    if meta.get("harness_id") == harness_id:
                        code_path = version_dir / "harness.py"
                        meta["code"] = code_path.read_text() if code_path.exists() else ""
                        return HarnessArtifact(**meta)
        return None

    def list_versions(self, environment: str) -> list[HarnessArtifact]:
        """List all harness versions for an environment."""
        env_dir = self._root / environment
        if not env_dir.exists():
            return []

        results = []
        for version_dir in sorted(env_dir.iterdir()):
            if not version_dir.is_dir() or not version_dir.name.startswith("v"):
                continue
            meta_path = version_dir / "metadata.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                code_path = version_dir / "harness.py"
                meta["code"] = code_path.read_text() if code_path.exists() else ""
                results.append(HarnessArtifact(**meta))
        return results

    def get_latest(self, environment: str) -> HarnessArtifact | None:
        """Get the latest (highest version) harness for an environment."""
        versions = self.list_versions(environment)
        if not versions:
            return None
        return max(versions, key=lambda a: a.version)

    def get_active(self, environment: str) -> HarnessArtifact | None:
        """Get the active harness for an environment."""
        active_link = self._root / environment / "active"
        if not active_link.exists():
            return None

        target = active_link.resolve()
        meta_path = target / "metadata.json"
        if not meta_path.exists():
            return None

        meta = json.loads(meta_path.read_text())
        code_path = target / "harness.py"
        meta["code"] = code_path.read_text() if code_path.exists() else ""
        return HarnessArtifact(**meta)

    def set_active(self, harness_id: str) -> None:
        """Set a harness as the active version for its environment."""
        artifact = self.load(harness_id)
        if artifact is None:
            raise ValueError(f"Harness not found: {harness_id}")

        version_dir = self._root / artifact.environment / f"v{artifact.version}"
        active_link = self._root / artifact.environment / "active"

        if active_link.exists():
            active_link.unlink()

        active_link.symlink_to(version_dir.resolve(), target_is_directory=True)

        self._update_lifecycle(harness_id, "ACTIVE")

    def update_metrics(self, harness_id: str, metrics: dict[str, float]) -> None:
        """Update evaluation metrics for a harness."""
        for env_dir in self._root.iterdir():
            if not env_dir.is_dir():
                continue
            for version_dir in env_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                meta_path = version_dir / "metadata.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    if meta.get("harness_id") == harness_id:
                        meta["evaluation_metrics"] = {
                            **meta.get("evaluation_metrics", {}),
                            **metrics,
                        }
                        meta_path.write_text(json.dumps(meta, indent=2))
                        return
        raise ValueError(f"Harness not found: {harness_id}")

    def update_static_validation(
        self, harness_id: str, validation_result: dict[str, object]
    ) -> None:
        """Record static validation result for a harness."""
        for env_dir in self._root.iterdir():
            if not env_dir.is_dir():
                continue
            for version_dir in env_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                meta_path = version_dir / "metadata.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    if meta.get("harness_id") == harness_id:
                        meta["static_validation"] = validation_result
                        meta_path.write_text(json.dumps(meta, indent=2))
                        return
        raise ValueError(f"Harness not found: {harness_id}")

    def _update_lifecycle(self, harness_id: str, state: str) -> None:
        """Update the lifecycle state of a harness."""
        for env_dir in self._root.iterdir():
            if not env_dir.is_dir():
                continue
            for version_dir in env_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                meta_path = version_dir / "metadata.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    if meta.get("harness_id") == harness_id:
                        meta["lifecycle_state"] = state
                        meta_path.write_text(json.dumps(meta, indent=2))
                        return
