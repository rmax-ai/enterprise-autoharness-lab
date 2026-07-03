"""Code-diff reporting between harness versions.

Produces unified diffs between harness source code versions
for provenance tracking and change analysis.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from autoharness_lab.harness.registry import HarnessRegistry


def diff_harness_versions(
    registry: HarnessRegistry,
    environment: str,
    version_a: int,
    version_b: int,
) -> str:
    """Generate a unified diff between two harness versions.

    Args:
        registry: HarnessRegistry containing the artifacts.
        environment: Environment name.
        version_a: Source version number.
        version_b: Target version number.

    Returns:
        Unified diff string.
    """
    versions = registry.list_versions(environment)
    version_map = {a.version: a for a in versions}

    artifact_a = version_map.get(version_a)
    artifact_b = version_map.get(version_b)

    if artifact_a is None:
        raise ValueError(f"Version {version_a} not found for environment {environment}")
    if artifact_b is None:
        raise ValueError(f"Version {version_b} not found for environment {environment}")

    return _unified_diff(
        artifact_a.code,
        artifact_b.code,
        from_label=f"v{version_a} ({artifact_a.harness_id[:12]})",
        to_label=f"v{version_b} ({artifact_b.harness_id[:12]})",
    )


def diff_parent_child(registry: HarnessRegistry, harness_id: str) -> str:
    """Generate a diff between a harness and its parent.

    Args:
        registry: HarnessRegistry containing the artifacts.
        harness_id: ID of the child harness.

    Returns:
        Unified diff string, or message if no parent exists.
    """
    child = registry.load(harness_id)
    if child is None:
        raise ValueError(f"Harness not found: {harness_id}")

    if child.parent_harness_id is None:
        return f"# No parent for harness {harness_id[:16]}... (initial generation)"

    parent = registry.load(child.parent_harness_id)
    if parent is None:
        return f"# Parent harness not found: {child.parent_harness_id[:16]}..."

    return _unified_diff(
        parent.code,
        child.code,
        from_label=f"parent ({parent.harness_id[:12]})",
        to_label=f"child ({child.harness_id[:12]})",
    )


def _unified_diff(a: str, b: str, from_label: str = "a", to_label: str = "b") -> str:
    """Generate a unified diff between two strings."""
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)

    diff = difflib.unified_diff(
        a_lines,
        b_lines,
        fromfile=from_label,
        tofile=to_label,
    )
    return "".join(diff)


def save_diff(
    diff_text: str,
    output_path: Path,
) -> Path:
    """Save a diff to a file.

    Returns:
        The path to the saved file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(diff_text)
    return output_path
