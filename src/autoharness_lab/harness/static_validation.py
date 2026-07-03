"""AST-based static validation for generated harness code.

Ensures harness code only uses safe Python constructs. Not a production
security boundary — documented as a research sandbox.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of static validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)

    @classmethod
    def success(cls) -> ValidationResult:
        return cls(valid=True)

    @classmethod
    def failure(cls, errors: list[str]) -> ValidationResult:
        return cls(valid=False, errors=errors)


# ── Forbidden constructs ────────────────────────────────────────────────

FORBIDDEN_BUILTINS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        "breakpoint",
        "input",
    }
)

FORBIDDEN_NAMES = frozenset(
    {
        "__class__",
        "__bases__",
        "__subclasses__",
        "__mro__",
        "__globals__",
        "__code__",
        "__closure__",
        "__dict__",
        "__builtins__",
    }
)

ALLOWED_MODULES = frozenset(
    {
        "json",
    }
)


class _HarnessValidator(ast.NodeVisitor):
    """AST walker that flags forbidden constructs."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self._has_evaluate_action = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] not in ALLOWED_MODULES:
                self.errors.append(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base = node.module.split(".")[0]
            if base not in ALLOWED_MODULES:
                self.errors.append(f"Forbidden import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
            self.errors.append(f"Forbidden builtin call: {node.func.id}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.attr, str) and node.attr in FORBIDDEN_NAMES:
            self.errors.append(f"Forbidden attribute access: .{node.attr}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name == "evaluate_action":
            self._has_evaluate_action = True
        self.generic_visit(node)


def validate_harness_code(code: str) -> ValidationResult:
    """Validate harness code against the AST whitelist.

    Checks:
    - Parseable Python
    - Contains evaluate_action function
    - No forbidden imports
    - No forbidden builtins (eval, exec, open, etc.)
    - No reflection (getattr, __dict__, etc.)

    Args:
        code: Raw harness source code string.

    Returns:
        ValidationResult with valid flag and error list.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ValidationResult.failure([f"Syntax error: {e}"])

    validator = _HarnessValidator()
    validator.visit(tree)

    if not validator._has_evaluate_action:
        validator.errors.append(
            "Missing required function: evaluate_action(observation, proposed_action)"
        )

    if validator.errors:
        return ValidationResult.failure(validator.errors)

    return ValidationResult.success()
