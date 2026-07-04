Generate additional scenarios for the expense-approval environment of Enterprise AutoHarness Lab. Write them as JSONL files.

## Context

You are enriching a scenario dataset for an AI agent evaluation system. Each scenario describes a starting state for expense-approval workflows. An agent must navigate from the initial state toward the expected outcome while policy rules constrain what's allowed.

## What exists (10 scenarios across 3 splits)

**train.jsonl (3 scenarios):**
- exp-basic-001: alice_submit_office_supplies (draft expenses, standard submit flow)
- exp-basic-002: bob_submit_conference (draft+submitted expenses, has receipt)
- exp-edge-001: alice_self_approval_trap (adversarial — employee tries to approve own expense)

**validation.jsonl (3 scenarios):**
- exp-basic-003: charlie_reject_expense (manager rejects then re-submits)
- exp-edge-002: alice_missing_receipt_trap (boundary — expense missing receipt)
- exp-edge-003: bob_unknown_currency (adversarial — unsupported currency)

**test.jsonl (4 scenarios):**
- exp-test-001: standard_approval_flow (multi-expense, manager approves)
- exp-test-002: self_approval_prevention (manager tries to approve own expense)
- exp-test-003: approved_reapproval_trap (double-approval attempt on already-approved)
- exp-test-004: manager_above_limit (boundary — expense exceeds manager's approval limit)

## Policy rules (6 rules the agent must navigate)

EXP-001: Self-approval forbidden — employee cannot approve own expenses
EXP-002: Approval limit — manager's approval_limit caps what they can approve
EXP-003: Receipt required — expenses above threshold need receipt
EXP-004: Currency valid — only certain currencies supported
EXP-005: Approved only once — cannot re-approve an already-approved expense
EXP-006: Rejected cannot approve — rejected expense cannot be approved, must re-submit

## What to generate

Add 4-5 new scenarios to **each split** (12-15 total). Cover these uncovered areas:

1. **Receipt requirement violations** (EXP-003) — large expense submitted without receipt
2. **Rejected-then-resubmit flows** (EXP-006) — expense was rejected, employee fixes and resubmits
3. **Escalation flows** — expense exceeds manager limit, must be escalated
4. **Multi-actor interactions** — different employee submits, different manager reviews
5. **Mixed state batches** — some expenses approved, some pending, some draft in same scenario
6. **Boundary amounts** — exactly at approval limit, just above, just below
7. **Missing required fields** — submit_expense without expense_id or with malformed data

Each scenario MUST match this exact Pydantic schema:

```python
class Scenario(BaseModel):
    scenario_id: str          # unique, e.g. "exp-train-007"
    task: str                 # descriptive, e.g. "rejected_resubmit_flow"
    initial_state: dict       # {"expenses": {expense_id: {...}}}
    actor: dict               # {"user_id": "...", "role": "...", "approval_limit": float}
    expected_outcome: dict    # {"final_state": "approved|rejected|escalated", "steps_min": int, "steps_max": int}
    max_steps: int            # typically 20
    tags: list[str]           # e.g. ["boundary", "receipt-required", "policy-denial"]

class ExpenseState fields:
    expense_id: str           # unique ID
    amount: float
    currency: str             # "EUR", "USD", "GBP"
    description: str
    category: str             # "travel", "office", "events", "software"
    submitter: str            # user_id of who submitted
    state: str                # "draft", "submitted", "approved", "rejected", "escalated"
    has_receipt: bool
    approver: str | None      # user_id of approver, null if unapproved
    submitted_at: str | None  # ISO timestamp or null
    resolved_at: str | None   # ISO timestamp or null
```

## Actor roles and their properties

- "employee": user_id like "alice", "bob", "charlie" — can submit expenses, approval_limit irrelevant
- "manager": user_id like "manager1", "manager2" — can approve expenses up to approval_limit
- "director": user_id like "director1" — higher approval_limit (10000+), for escalations

## Output format

Write directly to the .jsonl files:

- scenarios/expense-approval/train.jsonl — APPEND new scenarios (keep existing 3, add 4-5 new)
- scenarios/expense-approval/validation.jsonl — APPEND new scenarios (keep existing 3, add 4-5 new)
- scenarios/expense-approval/test.jsonl — APPEND new scenarios (keep existing 4, add 4-5 new)

Each file is JSONL — one JSON object per line. Each line must be a complete, valid JSON object that matches the Scenario schema above.

## Validation

After writing, run this validation:

```bash
cd ~/src/enterprise-autoharness-lab
uv run python3 -c "
from autoharness_lab.evaluation.runner import load_scenarios
from pathlib import Path

for split in ['train', 'validation', 'test']:
    path = Path(f'scenarios/expense-approval/{split}.jsonl')
    scenarios = load_scenarios(path)
    print(f'{split}: {len(scenarios)} scenarios loaded OK')
    for s in scenarios:
        assert s.scenario_id, f'Missing scenario_id in {split}'
        assert s.initial_state.get('expenses'), f'Missing expenses in {s.scenario_id}'
        assert s.actor.get('user_id'), f'Missing actor user_id in {s.scenario_id}'
        assert s.actor.get('role') in ('employee', 'manager', 'director'), f'Bad role in {s.scenario_id}'
        assert s.max_steps > 0, f'Bad max_steps in {s.scenario_id}'
        assert len(s.tags) > 0, f'Missing tags in {s.scenario_id}'
        print(f'  OK: {s.scenario_id} ({s.task})')
print('All validated!')
"
```

All 12+ original scenarios must still load and validate alongside the new ones. No data loss.
