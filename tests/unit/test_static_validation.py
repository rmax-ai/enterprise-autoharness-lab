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

    def test_accepts_generated_style_harness(self):
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
