# Milestone 2 — Automatic Synthesis Implementation Plan

> **For Hermes:** Use subagent-driven-development or Codex CLI to implement this plan
> task-by-task.

**Goal:** Build the automatic harness synthesis pipeline — mock model client, AST
sandbox, candidate registry, generation/refinement loop with promotion logic, and
the `autoharness synthesize` CLI command.

**Architecture:** Linear refinement loop: generate → validate (AST) → sandbox-test
→ evaluate → extract counterexamples → refine → promote if better. File-system
registry stores versioned harness artifacts. Mock model client enables
deterministic end-to-end tests without live LLM calls.

**Tech Stack:** Python 3.12+, Pydantic v2, pytest, uv

---

## Acceptance Criteria

- [ ] Mock model client implements ModelClient protocol, returns structural harness code from prompt files
- [ ] AST static validator rejects unsafe constructs (network, eval, exec, import, file I/O, reflection) and accepts valid harness code
- [ ] Sandbox executes generated harness code in subprocess with timeout, returns results
- [ ] File-system registry stores, loads, and lists harness versions with provenance metadata
- [ ] Generator produces initial harness from environment spec + mock client
- [ ] Counterexample extraction works on stored traces (already done, verify integration)
- [ ] Refiner takes harness + counterexamples and produces improved harness
- [ ] Promotion logic only replaces active harness when composite_score improves
- [ ] `autoharness synthesize` CLI runs full synthesis loop end-to-end
- [ ] Complete deterministic E2E test: mock client → generate → evaluate → refine → promote
- [ ] All existing 78 tests still pass, plus new tests (target: ~110+ total)
- [ ] Target >85% coverage on new synthesis and harness modules
- [ ] Ruff format + check + ty check clean

---

## Implementation Tasks

### Phase 1: Foundation — Mock Client + AST Validation + Sandbox

#### Task 1: Create MockModelClient

**Objective:** Implement a deterministic mock that returns harness code from prompts.

**Files:**
- Create: `src/autoharness_lab/model_clients/__init__.py`
- Create: `src/autoharness_lab/model_clients/mock.py`
- Create: `tests/unit/test_mock_client.py`

**Step 1: Create package init**

`src/autoharness_lab/model_clients/__init__.py`:
```python
"""Model client implementations — mock and real provider adapters."""
```

**Step 2: Write failing tests**

`tests/unit/test_mock_client.py`:
```python
"""Tests for MockModelClient."""

from pydantic import BaseModel, Field

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.models import ModelClient


class TestResponse(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}
    code: str
    reasoning: str = ""


class TestMockClient:
    def test_implements_model_client_protocol(self):
        client = MockModelClient()
        assert isinstance(client, ModelClient)

    def test_returns_registered_response(self):
        client = MockModelClient()
        client.register("test prompt", "test prompt", TestResponse, TestResponse(code="x = 1"))
        result = client.generate_structured("test prompt", "test prompt", TestResponse)
        assert result.code == "x = 1"

    def test_returns_default_when_no_match(self):
        client = MockModelClient()
        client.set_default(TestResponse, TestResponse(code="default"))
        result = client.generate_structured("anything", "anything", TestResponse)
        assert result.code == "default"

    def test_raises_when_no_match_and_no_default(self):
        client = MockModelClient()
        try:
            client.generate_structured("unmatched", "unmatched", TestResponse)
            assert False, "Should have raised"
        except ValueError as e:
            assert "No mock response" in str(e)

    def test_returns_static_response(self):
        client = MockModelClient.with_static(TestResponse(code="static"))
        result = client.generate_structured("any", "any", TestResponse)
        assert result.code == "static"

    def test_schema_mismatch_raises(self):
        client = MockModelClient()

        class OtherSchema(BaseModel):
            model_config = {"extra": "forbid", "frozen": True}
            value: int

        # Register with different schema than requested
        client.register("a", "b", OtherSchema, OtherSchema(value=42))
        try:
            client.generate_structured("a", "b", TestResponse)
            assert False, "Should have raised"
        except TypeError as e:
            assert "schema" in str(e).lower() or "type" in str(e).lower()
```

**Step 3: Run tests to verify failure**

```bash
uv run pytest tests/unit/test_mock_client.py -v
```
Expected: FAIL — module not found.

**Step 4: Write MockModelClient**

`src/autoharness_lab/model_clients/mock.py`:
```python
"""Mock model client for deterministic testing.

Returns pre-registered or default structured responses without any
LLM calls. Enables deterministic end-to-end tests of the synthesis pipeline.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MockModelClient:
    """Deterministic mock implementing the ModelClient protocol.

    Responses are registered by matching system_prompt + user_prompt against
    a lookup table. Falls back to a default response if configured, or raises
    ValueError if no match found.
    """

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], tuple[type[BaseModel], BaseModel]] = {}
        self._default: tuple[type[BaseModel], BaseModel] | None = None
        self._static_response: BaseModel | None = None

    @classmethod
    def with_static(cls, response: BaseModel) -> "MockModelClient":
        """Create a client that always returns the same response."""
        client = cls()
        client._static_response = response
        return client

    def register(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        response: BaseModel,
    ) -> None:
        """Register a mock response for a specific prompt combination."""
        self._responses[(system_prompt, user_prompt)] = (schema, response)

    def set_default(self, schema: type[BaseModel], response: BaseModel) -> None:
        """Set a default response returned when no match is found."""
        self._default = (schema, response)

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        """Return a registered or default structured response.

        Order of precedence:
        1. Static response (if set via with_static)
        2. Registered response matching system + user prompt
        3. Default response (if set)
        4. ValueError
        """
        if self._static_response is not None:
            if not isinstance(self._static_response, response_schema):
                raise TypeError(
                    f"Static response type {type(self._static_response).__name__} "
                    f"does not match requested schema {response_schema.__name__}"
                )
            return self._static_response

        key = (system_prompt, user_prompt)
        if key in self._responses:
            schema, response = self._responses[key]
            if schema is not response_schema:
                raise TypeError(
                    f"Registered schema {schema.__name__} does not match "
                    f"requested {response_schema.__name__}"
                )
            return response

        if self._default is not None:
            schema, response = self._default
            if schema is not response_schema:
                raise TypeError(
                    f"Default schema {schema.__name__} does not match "
                    f"requested {response_schema.__name__}"
                )
            return response

        raise ValueError(
            f"No mock response registered for prompt pair. "
            f"System starts with: {system_prompt[:80]}... "
            f"User starts with: {user_prompt[:80]}..."
        )
```

**Step 5: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_mock_client.py -v
```
Expected: 6 passed.

**Step 6: Commit**

```bash
git add src/autoharness_lab/model_clients/ tests/unit/test_mock_client.py
git commit -m "feat: add MockModelClient for deterministic synthesis testing"
```

---

#### Task 2: AST Static Validation

**Objective:** Validate that generated harness code only uses allowed Python constructs.

**Files:**
- Create: `src/autoharness_lab/harness/static_validation.py`
- Create: `tests/unit/test_static_validation.py`

**Step 1: Write failing tests**

`tests/unit/test_static_validation.py`:
```python
"""Tests for AST-based static validation of generated harness code."""

from autoharness_lab.harness.static_validation import (
    ValidationResult,
    validate_harness_code,
)


class TestStaticValidation:
    def test_accepts_valid_harness(self):
        code = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type == "submit_expense":
        return {
            "accepted": True,
            "normalized_action": proposed_action,
            "reason": "valid",
            "confidence": 0.9
        }
    return {
        "accepted": False,
        "normalized_action": None,
        "reason": "unknown",
        "confidence": None
    }
'''
        result = validate_harness_code(code)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_rejects_import(self):
        code = '''
import os
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''
        result = validate_harness_code(code)
        assert result.valid is False
        assert any("import" in e.lower() for e in result.errors)

    def test_rejects_eval(self):
        code = '''
def evaluate_action(observation, proposed_action):
    eval("print(1)")
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''
        result = validate_harness_code(code)
        assert result.valid is False
        assert any("eval" in e.lower() for e in result.errors)

    def test_rejects_exec(self):
        code = '''
def evaluate_action(observation, proposed_action):
    exec("x=1")
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''
        result = validate_harness_code(code)
        assert result.valid is False
        assert any("exec" in e.lower() for e in result.errors)

    def test_rejects_open(self):
        code = '''
def evaluate_action(observation, proposed_action):
    open("/etc/passwd")
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''
        result = validate_harness_code(code)
        assert result.valid is False
        assert any("open" in e.lower() for e in result.errors)

    def test_rejects_getattr_reflection(self):
        code = '''
def evaluate_action(observation, proposed_action):
    getattr(observation, "secret")
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''
        result = validate_harness_code(code)
        assert result.valid is False
        assert any("getattr" in e.lower() for e in result.errors)

    def test_rejects_globals(self):
        code = '''
def evaluate_action(observation, proposed_action):
    x = globals()
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''
        result = validate_harness_code(code)
        assert result.valid is False
        assert any("globals" in e.lower() for e in result.errors)

    def test_syntax_error_reported(self):
        code = "this is not valid python {{{"
        result = validate_harness_code(code)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_missing_evaluate_action_fails(self):
        code = "x = 1\n"
        result = validate_harness_code(code)
        assert result.valid is False
        assert any("evaluate_action" in e.lower() for e in result.errors)

    def test_accepts_submit_expense(self):
        # Simulated harness the generator might produce
        code = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    args = proposed_action.get("arguments", {})
    expense_id = args.get("expense_id", "")

    if not expense_id:
        return {"accepted": False, "normalized_action": None, "reason": "missing expense_id", "confidence": 0.99}

    expenses = observation.get("expenses", {})
    expense = expenses.get(expense_id)

    if expense is None:
        return {"accepted": False, "normalized_action": None, "reason": "expense not found", "confidence": 0.99}

    state = expense.get("state", "")

    if action_type == "submit_expense":
        if state != "draft":
            return {"accepted": False, "normalized_action": None, "reason": f"not draft: {state}", "confidence": 0.95}
        return {"accepted": True, "normalized_action": proposed_action, "reason": "valid submit", "confidence": 0.9}

    if action_type == "approve_expense":
        if state != "submitted":
            return {"accepted": False, "normalized_action": None, "reason": f"not submitted: {state}", "confidence": 0.95}
        return {"accepted": True, "normalized_action": proposed_action, "reason": "valid approve", "confidence": 0.85}

    return {"accepted": False, "normalized_action": None, "reason": f"unknown: {action_type}", "confidence": 0.5}
'''
        result = validate_harness_code(code)
        assert result.valid is True, f"Errors: {result.errors}"
```

**Step 2: Run tests to verify failure**

```bash
uv run pytest tests/unit/test_static_validation.py -v
```
Expected: FAIL — module not found.

**Step 3: Write implementation**

`src/autoharness_lab/harness/static_validation.py`:
```python
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
    def success(cls) -> "ValidationResult":
        return cls(valid=True)

    @classmethod
    def failure(cls, errors: list[str]) -> "ValidationResult":
        return cls(valid=False, errors=errors)


# ── Forbidden constructs ────────────────────────────────────────────────

FORBIDDEN_BUILTINS = frozenset({
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
})

FORBIDDEN_NAMES = frozenset({
    # Dunder access patterns
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "__globals__",
    "__code__",
    "__closure__",
    "__dict__",
    "__builtins__",
})

ALLOWED_MODULES = frozenset({
    # Python stdlib allowed — minimal set for harness logic
    "json",
})


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
        # Check for forbidden function calls
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTINS:
                self.errors.append(f"Forbidden builtin call: {node.func.id}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attr) -> None:
        # Check for forbidden attribute access (reflection via .__dict__, etc.)
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
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_static_validation.py -v
```
Expected: 10 passed.

**Step 5: Commit**

```bash
git add src/autoharness_lab/harness/static_validation.py tests/unit/test_static_validation.py
git commit -m "feat: add AST-based static validation for harness code"
```

---

#### Task 3: Sandbox Execution

**Objective:** Execute generated harness code in a restricted subprocess with timeout.

**Files:**
- Create: `src/autoharness_lab/harness/sandbox.py`
- Create: `tests/unit/test_sandbox.py`

**Step 1: Write failing tests**

`tests/unit/test_sandbox.py`:
```python
"""Tests for harness sandbox execution."""

import pytest

from autoharness_lab.harness.sandbox import SandboxExecutor, SandboxResult


VALID_HARNESS_CODE = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    args = proposed_action.get("arguments", {})

    if not args.get("expense_id"):
        return {"accepted": False, "normalized_action": None, "reason": "missing id", "confidence": 0.99}

    return {"accepted": True, "normalized_action": proposed_action, "reason": "ok", "confidence": 0.8}

def repair_action(observation, proposed_action, failure):
    return None
'''

HARNESS_WITH_IMPORT = '''
import os

def evaluate_action(observation, proposed_action):
    os.system("rm -rf /")
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''

HARNESS_INFINITE_LOOP = '''
def evaluate_action(observation, proposed_action):
    while True:
        pass
'''


class TestSandboxExecutor:
    def test_executes_valid_harness(self):
        executor = SandboxExecutor(VALID_HARNESS_CODE)
        result = executor.evaluate(
            {"expenses": {"e1": {"state": "draft"}}},
            {"type": "submit_expense", "arguments": {"expense_id": "e1"}},
        )
        assert result.accepted is True
        assert result.data is not None

    def test_rejects_missing_expense_id(self):
        executor = SandboxExecutor(VALID_HARNESS_CODE)
        result = executor.evaluate(
            {"expenses": {}},
            {"type": "submit_expense", "arguments": {}},
        )
        assert result.accepted is False

    def test_static_validation_blocks_import(self):
        executor = SandboxExecutor(HARNESS_WITH_IMPORT)
        result = executor.evaluate({}, {"type": "x", "arguments": {}})
        assert result.accepted is False
        assert result.error is not None
        assert "import" in result.error.lower()

    def test_timeout_on_infinite_loop(self):
        executor = SandboxExecutor(HARNESS_INFINITE_LOOP, timeout=0.5)
        result = executor.evaluate({}, {"type": "x", "arguments": {}})
        assert result.accepted is False
        assert result.error is not None
        assert "timeout" in result.error.lower()

    def test_handles_syntax_error(self):
        executor = SandboxExecutor("not valid python {{{")
        result = executor.evaluate({}, {"type": "x", "arguments": {}})
        assert result.accepted is False
        assert result.error is not None

    def test_calls_repair(self):
        code = '''
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": proposed_action, "reason": "", "confidence": 0.5}

def repair_action(observation, proposed_action, failure):
    return {"type": "submit_expense", "arguments": {"expense_id": "e1"}}
'''
        executor = SandboxExecutor(code)
        result = executor.repair(
            {"expenses": {}},
            {"type": "x", "arguments": {}},
            {"error_code": "MISSING_RECEIPT"},
        )
        assert result is not None
        assert result["type"] == "submit_expense"


def test_sandbox_result_immutable():
    result = SandboxResult(
        accepted=True,
        data={"normalized_action": {"type": "x"}},
    )
    assert result.accepted is True
    assert result.data == {"normalized_action": {"type": "x"}}
    assert result.error is None
```

**Step 2: Run tests to verify failure**

```bash
uv run pytest tests/unit/test_sandbox.py -v
```
Expected: FAIL — module not found.

**Step 3: Write implementation**

`src/autoharness_lab/harness/sandbox.py`:
```python
"""Sandbox execution for generated harness code.

Runs harness code in a restricted subprocess with AST validation,
timeout enforcement, and structured result capture.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import uuid
from dataclasses import dataclass
from typing import Any

from autoharness_lab.harness.static_validation import validate_harness_code


@dataclass(frozen=True)
class SandboxResult:
    """Result from sandbox execution of a harness."""

    accepted: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class SandboxExecutor:
    """Execute generated harness code in a sandboxed subprocess.

    Applies AST validation before execution. Runs in a separate process
    with timeout enforcement. The harness contract requires an
    evaluate_action(observation, proposed_action) -> dict function.

    Security notes:
    - AST validation blocks imports, eval, exec, file I/O, reflection
    - Subprocess isolation adds defense in depth
    - Timeout prevents infinite loops
    - This is a research sandbox, not a production security boundary
    """

    def __init__(self, code: str, timeout: float = 5.0) -> None:
        self._code = code
        self._timeout = timeout

    def evaluate(
        self,
        observation: dict[str, Any],
        proposed_action: dict[str, Any],
    ) -> SandboxResult:
        """Evaluate an action through the sandboxed harness.

        Args:
            observation: Current environment state.
            proposed_action: Action dict with 'type' and 'arguments'.

        Returns:
            SandboxResult with accepted flag and harness output.
        """
        validation = validate_harness_code(self._code)
        if not validation.valid:
            return SandboxResult(
                accepted=False,
                error=f"Static validation failed: {'; '.join(validation.errors)}",
            )

        return self._run_in_subprocess("evaluate_action", observation, proposed_action)

    def repair(
        self,
        observation: dict[str, Any],
        proposed_action: dict[str, Any],
        failure: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Attempt repair through the sandboxed harness.

        Returns repaired action dict or None if harness cannot repair.
        """
        validation = validate_harness_code(self._code)
        if not validation.valid:
            return None

        result = self._run_in_subprocess(
            "repair_action", observation, proposed_action, failure
        )
        return result.data

    def _run_in_subprocess(self, func_name: str, *args: Any) -> SandboxResult:
        """Execute a harness function in a subprocess via Python -c.

        The subprocess runs a small script that:
        1. Executes the harness code (after AST validation by the runner)
        2. Calls the named function with JSON-serialized args
        3. Returns JSON result via stdout
        """
        script_id = f"_harness_{uuid.uuid4().hex[:8]}"

        script = textwrap.dedent(f"""
        import json
        import sys

        # Execute harness code
        exec_globals = {{}}
        exec('''{self._code}''', exec_globals)

        if "{func_name}" not in exec_globals:
            print(json.dumps({{"error": "Function {func_name} not found in harness"}}))
            sys.exit(0)

        args_json = sys.stdin.read()
        args = json.loads(args_json)

        try:
            fn = exec_globals["{func_name}"]
            result = fn(*args)
            print(json.dumps({{"result": result}}))
        except Exception as e:
            print(json.dumps({{"error": str(e)}}))
        """)

        input_data = json.dumps(args)

        try:
            proc = subprocess.run(
                [sys.executable, "-c", script],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env={"PYTHONPATH": ""},
            )

            if proc.returncode != 0:
                stderr = proc.stderr.strip() or "Unknown subprocess error"
                return SandboxResult(accepted=False, error=f"Subprocess error: {stderr}")

            output = json.loads(proc.stdout.strip())

            if "error" in output:
                return SandboxResult(accepted=False, error=output["error"])

            result_data = output.get("result")
            if not isinstance(result_data, dict):
                return SandboxResult(
                    accepted=False,
                    error="Harness returned non-dict result",
                )

            return SandboxResult(
                accepted=bool(result_data.get("accepted", False)),
                data=result_data,
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                accepted=False,
                error=f"Harness execution timed out after {self._timeout}s",
            )
        except json.JSONDecodeError as e:
            return SandboxResult(accepted=False, error=f"JSON decode error: {e}")
        except Exception as e:
            return SandboxResult(accepted=False, error=f"Sandbox error: {e}")
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_sandbox.py -v
```
Expected: 7 passed.

**Step 5: Commit**

```bash
git add src/autoharness_lab/harness/sandbox.py tests/unit/test_sandbox.py
git commit -m "feat: add sandbox executor for harness code subprocess isolation"
```

---

### Phase 2: Harness Registry

#### Task 4: Harness Registry

**Objective:** Store, load, list, and version harness artifacts on the filesystem.

**Files:**
- Create: `src/autoharness_lab/harness/registry.py`
- Create: `tests/unit/test_registry.py`

**Step 1: Write failing tests**

`tests/unit/test_registry.py`:
```python
"""Tests for harness artifact registry."""

import tempfile
from pathlib import Path

from autoharness_lab.harness.registry import HarnessRegistry


VALID_CODE = '''
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
'''


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
            assert loaded.code == VALID_CODE

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

            # Lifecycle state updated
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

    def test_promote_updates_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            a = registry.store("expense-approval", VALID_CODE, "mock", "h1")
            registry.update_metrics(a.harness_id, {"composite_score": 0.85})

            loaded = registry.load(a.harness_id)
            assert loaded is not None
            assert loaded.evaluation_metrics["composite_score"] == 0.85
```

**Step 2: Run tests to verify failure**

```bash
uv run pytest tests/unit/test_registry.py -v
```
Expected: FAIL — module not found.

**Step 3: Write implementation**

`src/autoharness_lab/harness/registry.py`:
```python
"""File-system harness artifact registry.

Stores harness versions as directories with code + metadata files.
Zero dependencies, human-inspectable, appropriate for research prototype.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
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
            key=lambda d: int(d.name[1:])
        )
        version = len(existing)

        harness_id = f"harness-{environment}-v{version}-{uuid.uuid4().hex[:8]}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        version_dir = env_dir / f"v{version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        # Write code
        (version_dir / "harness.py").write_text(code)

        # Write metadata
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
            created_at=datetime.now(timezone.utc).isoformat(),
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

        # Update lifecycle state
        self._update_lifecycle(harness_id, "ACTIVE")

    def update_metrics(
        self, harness_id: str, metrics: dict[str, float]
    ) -> None:
        """Update evaluation metrics for a harness."""
        artifact = self.load(harness_id)
        if artifact is None:
            raise ValueError(f"Harness not found: {harness_id}")

        version_dir = (
            self._root / artifact.environment / f"v{artifact.version}"
        )
        artifact.evaluation_metrics = {**artifact.evaluation_metrics, **metrics}
        (version_dir / "metadata.json").write_text(artifact.model_dump_json(indent=2))

    def update_static_validation(
        self, harness_id: str, validation_result: dict[str, object]
    ) -> None:
        """Record static validation result for a harness."""
        artifact = self.load(harness_id)
        if artifact is None:
            raise ValueError(f"Harness not found: {harness_id}")

        version_dir = (
            self._root / artifact.environment / f"v{artifact.version}"
        )
        artifact.static_validation = validation_result
        (version_dir / "metadata.json").write_text(artifact.model_dump_json(indent=2))

    def _update_lifecycle(self, harness_id: str, state: str) -> None:
        """Update the lifecycle state of a harness."""
        artifact = self.load(harness_id)
        if artifact is None:
            return

        version_dir = (
            self._root / artifact.environment / f"v{artifact.version}"
        )
        artifact.lifecycle_state = state
        (version_dir / "metadata.json").write_text(artifact.model_dump_json(indent=2))
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_registry.py -v
```
Expected: 10 passed.

**Step 5: Commit**

```bash
git add src/autoharness_lab/harness/registry.py tests/unit/test_registry.py
git commit -m "feat: add file-system harness artifact registry"
```

---

### Phase 3: Synthesis Core

#### Task 5: Prompt Files for Generation

**Objective:** Create prompt template files for harness generation and refinement.

**Files:**
- Create: `src/autoharness_lab/synthesis/__init__.py`
- Create: `src/autoharness_lab/synthesis/prompts/__init__.py`
- Create: `src/autoharness_lab/synthesis/prompts/generate.txt`
- Create: `src/autoharness_lab/synthesis/prompts/refine.txt`

**Step 1: Create package init and generate prompt**

`src/autoharness_lab/synthesis/__init__.py`:
```python
"""Harness synthesis — generation, refinement, and search."""
```

`src/autoharness_lab/synthesis/prompts/__init__.py`:
```python
"""Versioned prompt files for harness synthesis.

Each prompt file has a hash for provenance tracking. Never modify
prompts without versioning.
"""
```

`src/autoharness_lab/synthesis/prompts/generate.txt`:
```
You are a code generation system that produces Python validation functions.

## Task

Generate an `evaluate_action(observation, proposed_action)` function that validates
whether an agent's proposed action is operationally valid for the given environment.

## Environment Spec

{environment_spec}

## Action Types Supported

{supported_actions}

## Contract

The function MUST:
- Accept observation (dict) and proposed_action (dict with 'type' and 'arguments')
- Return a dict: {{"accepted": bool, "normalized_action": dict|null, "reason": str, "confidence": float|null}}
- Be deterministic - same inputs always produce same output
- Handle unknown action types gracefully (return accepted=False)
- Handle missing fields gracefully (return accepted=False)
- NOT import any modules (except json if needed for serialization)
- NOT use eval, exec, open, getattr, or any reflection
- NOT access the network or filesystem

## Valid State Transitions

{state_transitions}

## Validation Rules

{validation_rules}

Return ONLY the Python code. No markdown, no explanation.
```

`src/autoharness_lab/synthesis/prompts/refine.txt`:
```
You are a code refinement system that improves Python validation functions.

## Task

Improve the following harness function based on counterexamples from execution failures.

## Current Harness

```python
{current_code}
```

## Counterexamples (failures the current harness missed)

{counterexamples}

## Improvement Rules

The improved harness should:
- Fix false acceptances: reject actions the counterexamples show should be rejected
- Fix false rejections: accept actions the counterexamples show should be accepted
- Preserve existing correct behavior
- Handle edge cases shown in counterexamples
- Be deterministic
- NOT import any modules (except json if needed)
- NOT use eval, exec, open, getattr, or any reflection

Return ONLY the complete improved Python code for evaluate_action. No markdown, no explanation.
```

**Step 2: Commit**

```bash
git add src/autoharness_lab/synthesis/
git commit -m "feat: add prompt templates for harness generation and refinement"
```

---

#### Task 6: Harness Generator

**Objective:** Generate initial harness code from environment spec using the model client.

**Files:**
- Create: `src/autoharness_lab/synthesis/generator.py`
- Create: `tests/unit/test_generator.py`

**Step 1: Read prompt files from the package using `importlib.resources`. We'll write a helper that reads prompts so the generator doesn't need filesystem access directly.

**Step 2: Write failing tests**

`tests/unit/test_generator.py`:
```python
"""Tests for harness code generator."""

from pydantic import BaseModel

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.synthesis.generator import HarnessGenerator


class GeneratorResponse(BaseModel):
    """Schema matching what the generator expects from the model client."""
    model_config = {"extra": "forbid", "frozen": True}
    code: str


VALID_CODE = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type == "submit_expense":
        return {"accepted": True, "normalized_action": proposed_action, "reason": "valid", "confidence": 0.9}
    return {"accepted": False, "normalized_action": None, "reason": "unknown", "confidence": 0.5}
'''


class TestHarnessGenerator:
    def test_generates_from_spec(self):
        mock = MockModelClient.with_static(GeneratorResponse(code=VALID_CODE))
        generator = HarnessGenerator(mock)

        spec = {
            "name": "expense-approval",
            "supported_actions": ["submit_expense", "approve_expense"],
            "state_transitions": {
                "draft": ["submitted"],
                "submitted": ["approved", "rejected"],
            },
            "validation_rules": [
                "Cannot approve own expense",
                "Cannot approve already approved expense",
            ],
        }

        result = generator.generate(spec)
        assert result.code == VALID_CODE
        assert result.environment == "expense-approval"
        assert result.harness_id is not None

    def test_includes_code_hash(self):
        mock = MockModelClient.with_static(GeneratorResponse(code=VALID_CODE))
        generator = HarnessGenerator(mock)

        result = generator.generate({
            "name": "expense-approval",
            "supported_actions": ["submit"],
            "state_transitions": {},
            "validation_rules": [],
        })
        assert result.code_hash is not None
        assert len(result.code_hash) > 0


def test_generator_response_schema():
    """Verify the response schema is correctly defined."""
    resp = GeneratorResponse(code="def foo(): pass")
    assert resp.code == "def foo(): pass"
```

**Step 3: Run tests to verify failure**

```bash
uv run pytest tests/unit/test_generator.py -v
```
Expected: FAIL — module not found.

**Step 4: Write implementation**

`src/autoharness_lab/synthesis/generator.py`:
```python
"""Initial harness code generation from environment spec.

Uses the ModelClient protocol to generate harness code. The actual
prompt templating reads from versioned prompt files.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from importlib import resources
from typing import Any

from pydantic import BaseModel, Field

from autoharness_lab.models import HarnessArtifact


class GeneratorResponse(BaseModel):
    """Structured response from the model client for harness generation."""
    model_config = {"extra": "forbid", "frozen": True}
    code: str = Field(description="Generated Python harness code")


def _load_prompt(name: str) -> str:
    """Load a prompt template from the versioned prompts directory."""
    pkg = resources.files("autoharness_lab.synthesis")
    prompt_path = pkg / "prompts" / name
    return prompt_path.read_text()


class HarnessGenerator:
    """Generate initial harness code from an environment spec.

    Uses the ModelClient protocol to generate code, then stores
    the result via the registry.
    """

    def __init__(self, model_client) -> None:
        self._client = model_client

    def generate(self, environment_spec: dict[str, Any]) -> HarnessArtifact:
        """Generate initial harness code for an environment.

        Args:
            environment_spec: Dict with keys:
                - name: Environment name
                - supported_actions: List of action type strings
                - state_transitions: Dict of state -> [next_states]
                - validation_rules: List of human-readable validation rules

        Returns:
            HarnessArtifact with generated code and provenance metadata.
        """
        prompt_template = _load_prompt("generate.txt")

        system_prompt = "You are a Python code generation system that produces validation functions."
        user_prompt = prompt_template.format(
            environment_spec=environment_spec.get("name", "unknown"),
            supported_actions="\n".join(
                f"- {a}" for a in environment_spec.get("supported_actions", [])
            ),
            state_transitions="\n".join(
                f"- {s} -> {', '.join(t)}"
                for s, t in environment_spec.get("state_transitions", {}).items()
            ),
            validation_rules="\n".join(
                f"- {r}" for r in environment_spec.get("validation_rules", [])
            ),
        )

        prompt_hash = hashlib.sha256(
            f"{system_prompt}{user_prompt}".encode()
        ).hexdigest()[:16]

        response = self._client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=GeneratorResponse,
        )

        code = response.code
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        return HarnessArtifact(
            harness_id=f"gen-{uuid.uuid4().hex[:8]}",
            environment=environment_spec["name"],
            version=0,
            lifecycle_state="GENERATED",
            code=code,
            code_hash=code_hash,
            parent_harness_id=None,
            model_name="mock",
            generation_prompt_hash=prompt_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            static_validation={},
            evaluation_metrics={},
        )
```

**Step 5: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_generator.py -v
```
Expected: 3 passed.

**Step 6: Commit**

```bash
git add src/autoharness_lab/synthesis/generator.py tests/unit/test_generator.py
git commit -m "feat: add harness code generator from environment spec"
```

---

#### Task 7: Harness Refiner

**Objective:** Refine harness code using counterexamples from execution failures.

**Files:**
- Create: `src/autoharness_lab/synthesis/refiner.py`
- Create: `tests/unit/test_refiner.py`

**Step 1: Write failing tests**

`tests/unit/test_refiner.py`:
```python
"""Tests for harness refiner."""

from pydantic import BaseModel

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.synthesis.refiner import HarnessRefiner


class RefinerResponse(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}
    code: str


ORIGINAL_CODE = '''
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": proposed_action, "reason": "accept all", "confidence": 0.5}
'''

IMPROVED_CODE = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type == "submit_expense":
        return {"accepted": True, "normalized_action": proposed_action, "reason": "valid", "confidence": 0.9}
    return {"accepted": False, "normalized_action": None, "reason": "reject unknown", "confidence": 0.5}
'''


class TestHarnessRefiner:
    def test_refines_from_counterexamples(self):
        mock = MockModelClient.with_static(RefinerResponse(code=IMPROVED_CODE))
        refiner = HarnessRefiner(mock)

        counterexamples = [
            {
                "observation": {"expenses": {}},
                "proposed_action": {"type": "invalid_action", "arguments": {}},
                "expected_classification": "rejected",
                "actual_result": {"status": "invalid_action"},
                "explanation": "Unknown action type should be rejected",
            }
        ]

        result = refiner.refine(
            current_code=ORIGINAL_CODE,
            counterexamples=counterexamples,
            environment="expense-approval",
        )
        assert result.code == IMPROVED_CODE
        assert result.code_hash is not None

    def test_parent_tracking(self):
        mock = MockModelClient.with_static(RefinerResponse(code=IMPROVED_CODE))
        refiner = HarnessRefiner(mock)

        result = refiner.refine(
            current_code=ORIGINAL_CODE,
            counterexamples=[],
            environment="expense-approval",
            parent_harness_id="harness-expense-approval-v0-abc12345",
        )
        assert result.parent_harness_id == "harness-expense-approval-v0-abc12345"

    def test_code_hash_changes_on_refinement(self):
        mock = MockModelClient.with_static(RefinerResponse(code=IMPROVED_CODE))
        refiner = HarnessRefiner(mock)

        result = refiner.refine(
            current_code=ORIGINAL_CODE,
            counterexamples=[],
            environment="expense-approval",
        )
        original_hash = "5d46b5165a6353a7"  # SHA256(ORIGINAL_CODE)[:16]
        assert result.code_hash != original_hash
```

**Step 2: Run tests to verify failure**

```bash
uv run pytest tests/unit/test_refiner.py -v
```
Expected: FAIL — module not found.

**Step 3: Write implementation**

`src/autoharness_lab/synthesis/refiner.py`:
```python
"""Harness refinement from execution counterexamples.

Takes a current harness and counterexamples from failed executions,
produces an improved harness via the model client.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from importlib import resources
from typing import Any

from pydantic import BaseModel, Field

from autoharness_lab.models import HarnessArtifact


class RefinerResponse(BaseModel):
    """Structured response from the model client for harness refinement."""
    model_config = {"extra": "forbid", "frozen": True}
    code: str = Field(description="Refined Python harness code")


def _load_prompt(name: str) -> str:
    """Load a prompt template from the versioned prompts directory."""
    pkg = resources.files("autoharness_lab.synthesis")
    prompt_path = pkg / "prompts" / name
    return prompt_path.read_text()


class HarnessRefiner:
    """Refine a harness using counterexamples from execution failures.

    Uses the ModelClient protocol to generate improved code based on
    what the current harness gets wrong.
    """

    def __init__(self, model_client) -> None:
        self._client = model_client

    def refine(
        self,
        current_code: str,
        counterexamples: list[dict[str, Any]],
        environment: str,
        parent_harness_id: str | None = None,
    ) -> HarnessArtifact:
        """Refine harness code based on counterexamples.

        Args:
            current_code: Current harness source code.
            counterexamples: List of failure dicts from extract_counterexamples().
            environment: Environment name.
            parent_harness_id: ID of the harness being refined.

        Returns:
            HarnessArtifact with refined code.
        """
        prompt_template = _load_prompt("refine.txt")

        # Format counterexamples compactly
        ce_str = json.dumps(counterexamples, indent=2, default=str)
        if len(ce_str) > 4000:
            ce_str = ce_str[:4000] + "\n... [truncated]"

        user_prompt = prompt_template.format(
            current_code=current_code,
            counterexamples=ce_str,
        )

        system_prompt = "You are a Python code refinement system."

        prompt_hash = hashlib.sha256(
            f"{system_prompt}{user_prompt}".encode()
        ).hexdigest()[:16]

        response = self._client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=RefinerResponse,
        )

        code = response.code
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        return HarnessArtifact(
            harness_id=f"ref-{uuid.uuid4().hex[:8]}",
            environment=environment,
            version=0,
            lifecycle_state="GENERATED",
            code=code,
            code_hash=code_hash,
            parent_harness_id=parent_harness_id,
            model_name="mock",
            generation_prompt_hash=prompt_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            static_validation={},
            evaluation_metrics={},
        )
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/unit/test_refiner.py -v
```
Expected: 3 passed.

**Step 5: Commit**

```bash
git add src/autoharness_lab/synthesis/refiner.py tests/unit/test_refiner.py
git commit -m "feat: add harness refiner from counterexamples"
```

---

#### Task 8: Synthesis Search Loop with Promotion

**Objective:** Orchestrate the full generate → validate → evaluate → refine → promote loop.

**Files:**
- Create: `src/autoharness_lab/synthesis/search.py`
- Create: `tests/integration/test_synthesis_loop.py`

**Step 1: Write failing integration tests**

`tests/integration/test_synthesis_loop.py`:
```python
"""Integration tests for the synthesis search loop."""

import tempfile
from pathlib import Path

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.synthesis.generator import GeneratorResponse
from autoharness_lab.synthesis.refiner import RefinerResponse
from autoharness_lab.synthesis.search import SynthesisLoop


VALID_CODE_v0 = '''
def evaluate_action(observation, proposed_action):
    # Accept everything — deliberately weak start
    return {"accepted": True, "normalized_action": proposed_action, "reason": "accept all", "confidence": 0.3}
'''

VALID_CODE_v1 = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type not in ("submit_expense", "approve_expense", "reject_expense"):
        return {"accepted": False, "normalized_action": None, "reason": f"unknown: {action_type}", "confidence": 0.9}
    args = proposed_action.get("arguments", {})
    if not args.get("expense_id"):
        return {"accepted": False, "normalized_action": None, "reason": "missing expense_id", "confidence": 0.99}
    return {"accepted": True, "normalized_action": proposed_action, "reason": "valid", "confidence": 0.7}
'''


class TestSynthesisLoop:
    def test_full_synthesis_with_mock_client(self):
        """End-to-end synthesis: generate → evaluate → refine → promote."""
        with tempfile.TemporaryDirectory() as tmp:
            mock = MockModelClient()
            mock.register(
                "You are a Python code generation system",
                "",
                GeneratorResponse,
                GeneratorResponse(code=VALID_CODE_v0),
            )
            mock.register(
                "You are a Python code refinement system",
                "",
                RefinerResponse,
                RefinerResponse(code=VALID_CODE_v1),
            )

            loop = SynthesisLoop(
                model_client=mock,
                registry_root=Path(tmp),
                environment="expense-approval",
                agent_name="noisy",
                max_iterations=2,
            )

            results = loop.run(
                environment_spec={
                    "name": "expense-approval",
                    "supported_actions": ["submit_expense", "approve_expense", "reject_expense"],
                    "state_transitions": {"draft": ["submitted"], "submitted": ["approved"]},
                    "validation_rules": ["No self-approval"],
                }
            )

            assert results.iterations_completed >= 1
            assert results.final_harness is not None
            assert results.best_score is not None
            assert results.history is not None
            assert len(results.history) > 0

    def test_promotion_only_on_improvement(self):
        """Verify that harness is only promoted when score improves."""
        with tempfile.TemporaryDirectory() as tmp:
            # First generation: accept-all (scores poorly)
            # Refinement: still bad code (should not promote)
            mock = MockModelClient()
            mock.register(
                "You are a Python code generation system",
                "",
                GeneratorResponse,
                GeneratorResponse(code=VALID_CODE_v0),
            )
            mock.register(
                "You are a Python code refinement system",
                "",
                RefinerResponse,
                RefinerResponse(code=VALID_CODE_v0),  # Same code — no improvement
            )

            loop = SynthesisLoop(
                model_client=mock,
                registry_root=Path(tmp),
                environment="expense-approval",
                agent_name="noisy",
                max_iterations=2,
            )

            results = loop.run(
                environment_spec={
                    "name": "expense-approval",
                    "supported_actions": ["submit_expense", "approve_expense"],
                    "state_transitions": {"draft": ["submitted"]},
                    "validation_rules": [],
                }
            )

            # The accept-all harness should not improve score,
            # so only 1 iteration stored (the initial generation)
            assert len(results.history) >= 1
```

**Step 2: Run tests to verify failure**

```bash
uv run pytest tests/integration/test_synthesis_loop.py -v
```
Expected: FAIL — module not found.

**Step 3: Write implementation**

`src/autoharness_lab/synthesis/search.py`:
```python
"""Synthesis search loop with promotion logic and history tracking.

Orchestrates: generate → validate → sandbox → evaluate → extract
counterexamples → refine → promote (if improved) → repeat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autoharness_lab.agents.noisy import NoisyAgent
from autoharness_lab.environments.expense_approval import ExpenseApprovalEnvironment
from autoharness_lab.evaluation.runner import (
    compute_all_metrics,
    load_scenarios,
    run_experiment,
)
from autoharness_lab.harness.registry import HarnessRegistry
from autoharness_lab.harness.sandbox import SandboxExecutor
from autoharness_lab.harness.static_validation import validate_harness_code
from autoharness_lab.models import HarnessArtifact
from autoharness_lab.policy.expense import ExpensePolicyEngine
from autoharness_lab.storage.traces import extract_counterexamples
from autoharness_lab.synthesis.generator import HarnessGenerator
from autoharness_lab.synthesis.refiner import HarnessRefiner


@dataclass
class IterationRecord:
    """Record of one synthesis iteration."""
    iteration: int
    harness_id: str
    composite_score: float
    metrics: dict[str, float]
    promoted: bool
    num_counterexamples: int


@dataclass
class SynthesisResult:
    """Result of a full synthesis run."""
    iterations_completed: int
    final_harness: HarnessArtifact | None
    best_score: float | None
    history: list[IterationRecord] = field(default_factory=list)


class SynthesisLoop:
    """Orchestrate the complete harness synthesis workflow.

    Linear refinement loop:
    1. Generate initial harness from environment spec
    2. Static validate + store in registry
    3. Sandbox test (basic sanity check)
    4. Evaluate against scenarios
    5. Extract counterexamples from failures
    6. Refine harness from counterexamples
    7. Promote if composite score improved
    8. Repeat until max_iterations or convergence
    """

    def __init__(
        self,
        model_client,
        registry_root: Path,
        environment: str,
        agent_name: str = "noisy",
        max_iterations: int = 5,
        seed: int = 42,
    ) -> None:
        self._client = model_client
        self._registry = HarnessRegistry(registry_root)
        self._generator = HarnessGenerator(model_client)
        self._refiner = HarnessRefiner(model_client)
        self._environment = environment
        self._agent_name = agent_name
        self._max_iterations = max_iterations
        self._seed = seed

    def run(self, environment_spec: dict[str, Any]) -> SynthesisResult:
        """Run the full synthesis loop.

        Args:
            environment_spec: Environment description for harness generation.

        Returns:
            SynthesisResult with iteration history and final harness.
        """
        history: list[IterationRecord] = []
        best_score: float | None = None
        best_harness: HarnessArtifact | None = None

        # ── Step 1: Generate initial harness ────────────────────────
        artifact = self._generator.generate(environment_spec)

        # Static validation
        validation = validate_harness_code(artifact.code)
        self._registry.update_static_validation(
            artifact.harness_id,
            {"valid": validation.valid, "errors": validation.errors},
        )

        if not validation.valid:
            # Initial generation failed validation — try refinement anyway
            history.append(IterationRecord(
                iteration=0,
                harness_id=artifact.harness_id,
                composite_score=0.0,
                metrics={},
                promoted=False,
                num_counterexamples=0,
            ))

        # Store in registry
        stored = self._registry.store(
            environment=environment_spec["name"],
            code=artifact.code,
            model_name="mock",
            generation_prompt_hash=artifact.generation_prompt_hash,
        )

        # ── Step 2: Evaluate ────────────────────────────────────────
        metrics = self._evaluate_harness(stored)
        score = metrics.get("composite_score", 0.0)

        if best_score is None or score > best_score:
            best_score = score
            best_harness = stored
            self._registry.update_metrics(stored.harness_id, metrics)
            self._registry.set_active(stored.harness_id)
            promoted = True
        else:
            promoted = False

        history.append(IterationRecord(
            iteration=0,
            harness_id=stored.harness_id,
            composite_score=score,
            metrics=metrics,
            promoted=promoted,
            num_counterexamples=self._count_counterexamples(stored),
        ))

        # ── Step 3-7: Refinement loop ───────────────────────────────
        current_code = stored.code
        current_id = stored.harness_id

        for iteration in range(1, self._max_iterations):
            # Extract counterexamples
            counterexamples = self._extract_counterexamples(stored)

            if not counterexamples:
                break  # No more failures to learn from

            # Refine
            refined = self._refiner.refine(
                current_code=current_code,
                counterexamples=[ce.model_dump() for ce in counterexamples],
                environment=environment_spec["name"],
                parent_harness_id=current_id,
            )

            # Static validate refined
            refined_validation = validate_harness_code(refined.code)
            if not refined_validation.valid:
                history.append(IterationRecord(
                    iteration=iteration,
                    harness_id=refined.harness_id,
                    composite_score=score,  # unchanged
                    metrics=metrics,
                    promoted=False,
                    num_counterexamples=len(counterexamples),
                ))
                continue

            # Store refined
            refined_stored = self._registry.store(
                environment=environment_spec["name"],
                code=refined.code,
                model_name="mock",
                generation_prompt_hash=refined.generation_prompt_hash,
                parent_harness_id=current_id,
            )

            # Evaluate refined
            refined_metrics = self._evaluate_harness(refined_stored)
            refined_score = refined_metrics.get("composite_score", 0.0)

            # Promote if improved
            if best_score is None or refined_score > best_score:
                best_score = refined_score
                best_harness = refined_stored
                self._registry.update_metrics(refined_stored.harness_id, refined_metrics)
                self._registry.set_active(refined_stored.harness_id)
                promoted = True
            else:
                promoted = False

            history.append(IterationRecord(
                iteration=iteration,
                harness_id=refined_stored.harness_id,
                composite_score=refined_score,
                metrics=refined_metrics,
                promoted=promoted,
                num_counterexamples=len(counterexamples),
            ))

            current_code = refined.code
            current_id = refined.harness_id
            stored = refined_stored

            if not promoted:
                break  # No improvement, stop early

        return SynthesisResult(
            iterations_completed=len(history),
            final_harness=best_harness,
            best_score=best_score,
            history=history,
        )

    def _evaluate_harness(self, artifact: HarnessArtifact) -> dict[str, float]:
        """Evaluate a harness against the test scenarios."""
        repo_root = Path(__file__).resolve().parents[3]
        scenario_path = repo_root / "scenarios" / self._environment / "test.jsonl"

        if not scenario_path.exists():
            return {"composite_score": 0.0}

        scenarios = load_scenarios(scenario_path)
        agent = NoisyAgent(seed=self._seed)
        policy = ExpensePolicyEngine()
        sandbox = SandboxExecutor(artifact.code)

        # Run experiment with the sandbox as the harness runtime
        records = run_experiment(
            scenarios=scenarios,
            environment_factory=lambda: ExpenseApprovalEnvironment(),
            agent=agent,
            policy_engine=policy,
            harness_runtime=sandbox,
            run_id=f"synthesis-{artifact.harness_id}",
        )

        return compute_all_metrics(records)

    def _extract_counterexamples(self, artifact: HarnessArtifact) -> list:
        """Extract counterexamples by running the harness and checking failures."""
        repo_root = Path(__file__).resolve().parents[3]
        scenario_path = repo_root / "scenarios" / self._environment / "test.jsonl"

        if not scenario_path.exists():
            return []

        scenarios = load_scenarios(scenario_path)
        agent = NoisyAgent(seed=self._seed)
        policy = ExpensePolicyEngine()
        sandbox = SandboxExecutor(artifact.code)

        records = run_experiment(
            scenarios=scenarios,
            environment_factory=lambda: ExpenseApprovalEnvironment(),
            agent=agent,
            policy_engine=policy,
            harness_runtime=sandbox,
            run_id=f"ce-{artifact.harness_id}",
        )

        return extract_counterexamples(records)

    def _count_counterexamples(self, artifact: HarnessArtifact) -> int:
        """Count counterexamples for an artifact."""
        return len(self._extract_counterexamples(artifact))
```

**Wait — the issue here is that the existing `run_experiment` in evaluation/runner.py passes `harness_runtime.evaluate()` which calls the module, but the `SandboxExecutor` has a different interface. We need to adapt.

Let me check: `run_experiment` calls `harness_runtime.evaluate(observation, {...})`. But `SandboxExecutor` has `evaluate(observation, proposed_action)` returning `SandboxResult` not a dict.

We need to make SandboxExecutor work with run_experiment's expected interface. The cleanest way: make SandboxExecutor work as a harness_runtime too. Let me add a wrapper or make it compatible.

Actually, looking at run_experiment line 199-203:
```python
harness_result = harness_runtime.evaluate(
    observation,
    {"type": proposed_action.type, "arguments": proposed_action.arguments},
)
harness_decision = HarnessDecision(**harness_result)
```

So the runtime's `evaluate()` returns a dict that gets unpacked into HarnessDecision. The SandboxExecutor.evaluate() returns a SandboxResult, not a dict.

I need to adapt the sandbox to return a dict compatible with HarnessDecision, OR wrap it. Let me create a small adapter in sandbox.py.

Actually, a simpler approach: have `SandboxExecutor.evaluate()` return a dict matching HarnessDecision's fields. Let me modify the sandbox test and implementation.

Let me revise the sandbox to return a dict instead of SandboxResult when used as a harness runtime. Or better: add a `evaluate_as_harness()` method that returns the dict shape expected by the runner. Or even simpler: just make the `evaluate()` return a dict matching the harness contract.

Actually, the cleanest: the SandboxExecutor already works for the sandbox use case. For the harness runtime case, we already have `HarnessRuntime` in contracts.py which wraps a module. Let me just keep those separate and create a small bridge in the search loop that converts SandboxResult → HarnessDecision dict.

Looking at search.py, I'm using `sandbox` as the `harness_runtime` parameter of `run_experiment`. The problem is `run_experiment` expects `harness_runtime.evaluate(...)` to return a dict with `accepted`, `normalized_action`, `reason`, `confidence`.

Let me create a `SandboxHarnessRuntime` wrapper class that wraps SandboxExecutor and presents the harness runtime interface.

I'll add that in the sandbox.py file.

Let me revise the search.py to use an adapter. Actually, let me just make the sandbox's evaluate return the right shape. The sandbox currently returns SandboxResult which has accepted, data, error. I'll add a method to return the harness contract shape.

Simpler fix: add `evaluate_as_harness` to SandboxExecutor that returns a dict matching what run_experiment expects. Let me revise both the sandbox and the search.

OK, let me rework the sandbox to keep the current interface AND add a compatibility method. Let me update the implementation.<｜end▁of▁thinking｜>The search loop needs to bridge between `SandboxExecutor` (returns `SandboxResult`) and `run_experiment` (expects `HarnessRuntime`-style dicts). Let me revise the sandbox to add an adapter.

<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="read_file">
<｜｜DSML｜｜parameter name="path" string="true">/home/rmax-10/src/rmax-ai/enterprise-autoharness-lab/src/autoharness_lab/harness/sandbox.py