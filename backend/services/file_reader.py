from __future__ import annotations

import ast
import json
from pathlib import Path


async def read_jsonl(path: Path) -> list[dict[str, object]]:
    """Read JSONL file, return list of parsed dicts."""
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


async def read_json(path: Path) -> dict[str, object]:
    """Read JSON file, return parsed dict."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def discover_environments(workspace_root: Path) -> list[dict[str, object]]:
    """Scan scenarios/ dir for environment directories and their splits."""
    scenarios_root = workspace_root / "scenarios"
    environments_root = workspace_root / "src" / "autoharness_lab" / "environments"
    discovered: list[dict[str, object]] = []

    for module_path in sorted(environments_root.glob("*.py")):
        if module_path.name == "__init__.py":
            continue

        env_id = module_path.stem.replace("_", "-")
        env_dir = scenarios_root / env_id
        description = f"{env_id.replace('-', ' ').title()} environment"
        action_count = 0

        parsed = ast.parse(module_path.read_text(encoding="utf-8"))
        module_doc = ast.get_docstring(parsed)
        if module_doc:
            description = module_doc.splitlines()[0].strip().rstrip(".")
        for node in parsed.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SUPPORTED_ACTIONS":
                        action_value = ast.literal_eval(node.value)
                        action_count = len(action_value)

        counts = {"train": 0, "validation": 0, "test": 0}
        if env_dir.exists():
            for split_name in counts:
                split_path = env_dir / f"{split_name}.jsonl"
                if split_path.exists():
                    with split_path.open("r", encoding="utf-8") as handle:
                        counts[split_name] = sum(1 for line in handle if line.strip())

        discovered.append(
            {
                "id": env_id,
                "name": env_id.replace("-", " ").title(),
                "description": description,
                "action_count": action_count,
                "scenario_counts": counts,
                "status": "ready" if any(counts.values()) else "missing-data",
            }
        )

    return discovered


def load_policy_rules(workspace_root: Path, env_id: str) -> list[dict[str, object]]:
    """Parse policy rules from the policy module."""
    policy_name = env_id.split("-")[0]
    policy_path = workspace_root / "src" / "autoharness_lab" / "policy" / f"{policy_name}.py"
    if not policy_path.exists():
        return []

    parsed = ast.parse(policy_path.read_text(encoding="utf-8"))
    rules: list[dict[str, object]] = []

    for node in parsed.body:
        if not isinstance(node, ast.Assign):
            continue
        target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if not target_names or not target_names[0].startswith("RULE_"):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue

        rule: dict[str, object] = {}
        for keyword in call.keywords:
            if keyword.arg in {"rule_id", "description", "priority"}:
                rule[keyword.arg] = ast.literal_eval(keyword.value)
        if {"rule_id", "description", "priority"} <= rule.keys():
            rules.append(rule)

    return sorted(rules, key=lambda item: int(item["priority"]))
