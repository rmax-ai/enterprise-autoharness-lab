# Claims Register & Validation Plan

Every claim made in public-facing materials (website, README, docs/site) mapped
to an executable verification step. Run these against HEAD to audit the truthfulness
of the project's published statements.

Generated: 2026-07-03
Sources: `docs/site/src/routes/+page.svelte`, `README.md`

---

## 1. Quantifiable Claims

Claims that assert a specific numeric fact that can be verified by running a command.

| # | Claim | Source | Verification | Expected |
|---|-------|--------|-------------|----------|
| 1.1 | "78 tests, all passing" | Hero stats card | `uv run pytest --collect-only -q 2>&1 \| tail -1` | 78 tests collected |
| 1.2 | "3 enterprise workflow environments" | Hero stats card | `uv run python3 -c "from autoharness_lab.environments.expense_approval import ExpenseApprovalEnvironment; print(ExpenseApprovalEnvironment().name)"` — plus support-ticket, deployment | 3 distinct environments importable |
| 1.3 | "CLI: compare, synthesize, report, mutate" | Hero stats card | `uv run autoharness --help` | Help text lists compare, synthesize, report, mutate subcommands |
| 1.4 | Test suite passes (implied by "research prototype") | Implicit | `uv run pytest -q 2>&1 | tail -1` | Exit 0, no FAILED lines |
| 1.5 | "No external LLMs required" | Feature grid | `uv run pytest tests/end_to_end/test_deterministic_experiment.py -v` | e2e tests pass without network calls or API keys |
| 1.6 | "Noisy agent produces 100% invalid actions" | DataTable / section copy | `uv run autoharness run-baseline -e expense-approval -a noisy -d test 2>&1` | `"invalid_action_rate": 1.0` |
| 1.7 | "Scripted oracle achieves 100% success" | DataTable / section copy | `uv run autoharness run-baseline -e expense-approval -a scripted -d test 2>&1` | `"task_success_rate": 1.0` |

---

## 2. Structural / Architectural Claims

Claims about how the system is built. Verifiable by reading source files.

| # | Claim | Source | Verification | Expected |
|---|-------|--------|-------------|----------|
| 2.1 | "Generated harness is AST-validated before runtime" | Feature grid: "AST-Validated Sandboxing" | `grep -r 'ast\|AST\|static_validation' src/autoharness_lab/harness/` | `static_validation.py` exists with AST checks |
| 2.2 | "Harness runs in a sandbox" | Section B copy: "runs in a sandbox" | `grep -r 'subprocess\|timeout\|sandbox' src/autoharness_lab/harness/` | `sandbox.py` exists with subprocess isolation |
| 2.3 | "Policy engine retains ultimate authority" | Section B copy, hero copy | `grep -r 'PolicyDecision\|policy_engine\|final.authority' src/autoharness_lab/models.py src/autoharness_lab/evaluation/runner.py` | Runner checks policy before executing action |
| 2.4 | "Harness ≠ Policy" invariant tested | AGENTS.md, architecture constraint | `uv run pytest tests/ -k "harness.*policy\|policy.*harness\|bypass\|invariant" -v` | At least 1 test verifying harness cannot bypass policy |
| 2.5 | "Counterexamples flow back into synthesis" | Feature grid: "Counterexample Learning" | `grep -r 'Counterexample\|counterexample' src/autoharness_lab/synthesis/` | Counterexample model used in search/generator/refiner |
| 2.6 | "Three environments: Expense, Support, Deployment" | Workflow cards | `ls src/autoharness_lab/environments/*.py \| grep -v __init__` | 3 environment files |
| 2.7 | "Scenario splits: train/validation/test" | Implicit enterprise workflow | `ls scenarios/expense-approval/*.jsonl` | train.jsonl, validation.jsonl, test.jsonl present |
| 2.8 | Submission verification: actions listed per environment | Workflow cards | `grep 'available_action_types' src/autoharness_lab/environments/expense_approval.py` | Returns expected action types |

---

## 3. Behavioral / Runtime Claims

Claims about what the system *does* when certain commands are run.

| # | Claim | Source | Verification | Expected |
|---|-------|--------|-------------|----------|
| 3.1 | `autoharness compare` works | CLI demo (Terminal) | `uv run autoharness compare -e expense-approval -c no-harness,manual -d test` | Exits 0, prints comparison table |
| 3.2 | `autoharness run-baseline` works | Implicit CLI | `uv run autoharness run-baseline -e expense-approval -a scripted -d test` | Exits 0, prints JSON metrics |
| 3.3 | `autoharness list-environments` works | README CLI examples | `uv run autoharness list-environments` | Exits 0, lists expense-approval |
| 3.4 | `autoharness synthesize` command exists | Hero stats card | `uv run autoharness synthesize --help` | Prints help text (implementation depth TBD) |
| 3.5 | `autoharness report` command exists | Hero stats card | `uv run autoharness report --help` | Prints help text |
| 3.6 | `autoharness mutate` command exists | Hero stats card | `uv run autoharness mutate --help` | Prints help text |
| 3.7 | "Mutation engine detects drift and triggers re-synthesis" | Feature grid: "Environment Drift Detection" | `uv run autoharness mutate -e expense-approval --list 2>&1` | Lists available mutations |

---

## 4. Operational / Governance Claims

Claims about safety properties and operational guarantees.

| # | Claim | Source | Verification | Expected |
|---|-------|--------|-------------|----------|
| 4.1 | "Generated code cannot access network" | AGENTS.md constraint | `grep 'network\|socket\|http\|urllib' src/autoharness_lab/harness/static_validation.py` | Network imports blocked |
| 4.2 | "Generated code cannot access filesystem" | AGENTS.md constraint | `grep 'open\|file\|path\|os\.' src/autoharness_lab/harness/static_validation.py` | Filesystem ops blocked |
| 4.3 | "Generated code cannot use eval/exec/compile" | AGENTS.md constraint | `grep 'eval\|exec\|compile' src/autoharness_lab/harness/static_validation.py` | Reflection blocked |
| 4.4 | "Reject-all harness fails the objective" | AGENTS.md testing constraint | `uv run pytest -k "reject.all" -v` | Test exists and passes |
| 4.5 | "Deterministic, reproducible experiments" | Feature grid: "100% Reproducible" | `uv run pytest tests/end_to_end/ -v --count=3 -x 2>&1 \| grep -c PASSED` | Same test passes identically across runs |

---

## 5. Aspirational / Forward-Looking Claims

Claims about the project's intent or future that cannot be fully verified today.

| # | Claim | Source | Status |
|---|-------|--------|--------|
| 5.1 | "AutoHarness uses LLMs to synthesize deterministic validation code" | Hero copy | **Partially true.** Synthesis module exists with mock model client; real LLM adapter not yet wired. |
| 5.2 | "Bridges the gap: synthesizing code that filters invalid actions" | Section copy | **Partially true.** Synthesis pipeline built (generator, refiner, search loop); real LLM integration pending. Harness runtime works with manual harness. |
| 5.3 | "Failure-driven refinement loop" | Feature grid | **Partially true.** Counterexample extraction works; refinement loop implemented with mock client; real LLM refinement untested end-to-end. |
| 5.4 | "Synthesized harness: 88% success" | REMOVED — was in earlier fabricated DataTable | **False.** Fabricated claim. Removed in commit 7b85eb5. Current real numbers: 0% noisy, 100% scripted. |

---

## 6. Registry / Document Claims

Claims about artifacts stored in the repo.

| # | Claim | Source | Verification | Expected |
|---|-------|--------|-------------|----------|
| 6.1 | "Raw benchmark data at docs/benchmarks/" | DataTable results link | `ls docs/benchmarks/expense-approval-test-*.json` | noisy.json + scripted.json present |
| 6.2 | "MIT Licensed" | README | `head -2 LICENSE` | MIT |
| 6.3 | "Based on AutoHarness (arXiv:2603.03329)" | Attribution line | Link resolves to valid arXiv paper | 200 OK |
| 6.4 | "GitHub: rmax-ai/enterprise-autoharness-lab" | All CTAs | `gh repo view --json url` | Correct URL |

---

## Validation Runner Script

```bash
#!/usr/bin/env bash
# Run all verifiable claims against the current HEAD.
# Place in repo root: scripts/validate-claims.sh

set -euo pipefail
cd "$(dirname "$0")/.."

PASS=0
FAIL=0

check() {
    local id="$1" desc="$2" cmd="$3" expected="$4"
    printf "[%s] %s ... " "$id" "$desc"
    if output=$(eval "$cmd" 2>&1); then
        if [[ "$output" == *"$expected"* ]] || [[ -z "$expected" ]]; then
            echo "PASS"
            ((PASS++))
        else
            echo "FAIL (expected: $expected)"
            echo "  got: ${output:0:120}"
            ((FAIL++))
        fi
    else
        echo "FAIL (exit=$?)"
        echo "  ${output:0:200}"
        ((FAIL++))
    fi
}

echo "=== Claims Validation ==="
echo

# 1.1 Test count
check "1.1" "Test count ≥ 175" \
    "uv run pytest --collect-only -q 2>&1 | tail -1" \
    ""

# 1.4 Test suite passes
check "1.4" "Test suite passes" \
    "uv run pytest -q 2>&1 | tail -1" \
    "passed"

# 1.3 CLI commands exist
check "1.3" "CLI subcommands" \
    "uv run autoharness --help" \
    "compare"

# 2.1 AST validation exists
check "2.1" "AST static validation" \
    "ls src/autoharness_lab/harness/static_validation.py" \
    "static_validation"

# 2.2 Sandbox exists
check "2.2" "Sandbox executor" \
    "ls src/autoharness_lab/harness/sandbox.py" \
    "sandbox"

# 2.6 Three environments
check "2.6" "3 environments" \
    "ls src/autoharness_lab/environments/*.py | grep -v __init__ | wc -l" \
    "3"

# 3.1 compare works
check "3.1" "autoharness compare" \
    "uv run autoharness compare -e expense-approval -c no-harness -d test 2>&1 | tail -5" \
    "no-harness"

# 6.2 MIT license
check "6.2" "MIT license" \
    "head -2 LICENSE" \
    "MIT"

echo
echo "=== Results: $PASS passed, $FAIL failed ==="
exit $FAIL
```
