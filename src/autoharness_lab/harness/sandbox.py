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

    Two evaluation interfaces:
    - evaluate() -> SandboxResult: structured result for standalone use
    - evaluate_as_harness() -> dict: HarnessDecision-compatible dict for
      use as a harness_runtime in run_experiment()

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
        return self._eval_internal(observation, proposed_action)

    def evaluate_as_harness(
        self,
        observation: dict[str, Any],
        proposed_action: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate an action, returning HarnessDecision-compatible dict.

        This method is designed to be used as the harness_runtime parameter
        in run_experiment(). Returns a dict that can be unpacked into
        HarnessDecision(**result).

        Args:
            observation: Current environment state.
            proposed_action: Action dict with 'type' and 'arguments'.

        Returns:
            Dict with keys: accepted, normalized_action, reason, confidence.
        """
        result = self._eval_internal(observation, proposed_action)
        if result.error:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": result.error,
                "confidence": None,
            }
        if result.data:
            return {
                "accepted": result.data.get("accepted", False),
                "normalized_action": result.data.get("normalized_action"),
                "reason": result.data.get("reason", ""),
                "confidence": result.data.get("confidence"),
            }
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": "No harness output",
            "confidence": None,
        }

    def _eval_internal(
        self,
        observation: dict[str, Any],
        proposed_action: dict[str, Any],
    ) -> SandboxResult:
        """Internal evaluation — applies AST validation then subprocess execution."""
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

        Encodes the harness code as base64 to avoid escaping issues.
        The subprocess decodes, executes, calls the function, and
        returns JSON via stdout.
        """
        import base64

        code_b64 = base64.b64encode(self._code.encode()).decode()

        script = textwrap.dedent(f"""\
        import base64
        import json
        import sys

        code = base64.b64decode("{code_b64}").decode()
        exec_globals = {{}}
        exec(code, exec_globals)

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
