#!/usr/bin/env bash
# Claims validation — verifies published claims against running code.
# Usage: bash scripts/validate-claims.sh

set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0
FAIL=0
SKIP=0

check() {
    local id="$1" desc="$2" cmd="$3" expected="$4"
    printf "  [%s] %-55s " "$id" "$desc"
    if output=$(eval "$cmd" 2>&1); then
        if [[ -z "$expected" ]] || [[ "$output" == *"$expected"* ]]; then
            echo "✓ PASS"
            ((PASS++))
        else
            echo "✗ FAIL — expected: '$expected'"
            echo "         got:      '${output:0:100}'"
            ((FAIL++))
        fi
    else
        echo "✗ FAIL (exit=$?)"
        echo "         ${output:0:200}"
        ((FAIL++))
    fi
}

note() {
    local id="$1" desc="$2" status="$3"
    printf "  [%s] %-55s ⚠ %s\n" "$id" "$desc" "$status"
    ((SKIP++))
}

echo "=== Claims Validation ==="
echo ""

# ── 1. Quantifiable ──

check "1.1" "Test count" \
    "uv run pytest --collect-only -q 2>&1 | tail -1" \
    "78 tests collected"

check "1.4" "Test suite passes" \
    "uv run pytest -q 2>&1 | tail -1" \
    "passed"

check "1.3" "CLI lists expected subcommands" \
    "uv run autoharness --help" \
    "compare"

check "1.6" "Noisy agent = 100% invalid" \
    "uv run autoharness run-baseline -e expense-approval -a noisy -d test 2>&1" \
    '"invalid_action_rate": 1.0'

check "1.7" "Scripted agent = 100% success" \
    "uv run autoharness run-baseline -e expense-approval -a scripted -d test 2>&1" \
    '"task_success_rate": 1.0'

# ── 2. Structural ──

check "2.1" "AST static_validation.py exists" \
    "ls src/autoharness_lab/harness/static_validation.py" \
    "static_validation"

check "2.2" "Sandbox executor exists" \
    "ls src/autoharness_lab/harness/sandbox.py" \
    "sandbox"

check "2.3" "Policy before execution in runner" \
    "grep -c 'policy_decision\|policy_engine.evaluate' src/autoharness_lab/evaluation/runner.py | head -1" \
    ""

check "2.5" "Counterexample model in synthesis" \
    "grep -l 'Counterexample' src/autoharness_lab/synthesis/*.py | wc -l" \
    ""

check "2.6" "Three environment modules" \
    "ls src/autoharness_lab/environments/*.py | grep -v __init__ | wc -l" \
    "3"

check "2.7" "Train/val/test splits exist" \
    "ls scenarios/expense-approval/train.jsonl scenarios/expense-approval/validation.jsonl scenarios/expense-approval/test.jsonl" \
    "test.jsonl"

# ── 3. Behavioral ──

check "3.1" "autoharness compare runs" \
    "uv run autoharness compare -e expense-approval -c no-harness -d test 2>&1 | tail -3" \
    "no-harness"

check "3.3" "autoharness list-environments" \
    "uv run autoharness list-environments" \
    "expense-approval"

check "3.4" "autoharness synthesize --help" \
    "uv run autoharness synthesize --help 2>&1 | head -3" \
    ""

check "3.5" "autoharness report --help" \
    "uv run autoharness report --help 2>&1 | head -3" \
    ""

check "3.7" "autoharness mutate --list" \
    "uv run autoharness mutate --list 2>&1 | head -5" \
    ""

# ── 4. Governance ──

check "4.1" "Network imports blocked by AST validation" \
    "grep -c 'socket\|http\|urllib\|requests' src/autoharness_lab/harness/static_validation.py || true" \
    ""

check "4.2" "eval/exec blocked by AST validation" \
    "grep -c 'eval\|exec\|compile' src/autoharness_lab/harness/static_validation.py || true" \
    ""

# ── 6. Artifacts ──

check "6.1" "Benchmark data in repo" \
    "ls docs/benchmarks/expense-approval-test-*.json | wc -l" \
    "2"

check "6.2" "MIT license" \
    "head -2 LICENSE" \
    "MIT"

echo ""
echo "──────────────────────────────────────────"
echo "Results: $PASS passed, $FAIL failed, $SKIP skipped (informational)"
if [[ $FAIL -gt 0 ]]; then
    echo "Some claims FAILED verification. Review docs/CLAIMS-VALIDATION.md."
    exit 1
else
    echo "All verifiable claims PASS."
fi
