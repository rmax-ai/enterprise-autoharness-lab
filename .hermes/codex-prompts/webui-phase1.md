Implement Phase 1 of the Enterprise AutoHarness Lab web application — the **Foundation & Read-Only State** layer.

## Architecture

Decoupled SPA + API:
- **Backend:** FastAPI at `backend/` serving existing benchmark + scenario data
- **Frontend:** SvelteKit static app at `docs/site/` with new `/lab/*` routes
- Frontend fetches from backend via configurable `VITE_API_BASE_URL`

## Phase 1 Scope

### Backend files to create

**1. `backend/main.py`** — FastAPI app with CORS, mounts routers
**2. `backend/config.py`** — Pydantic BaseSettings with `WORKSPACE_ROOT` (defaults to repo root)
**3. `backend/models/benchmark.py`** — Pydantic schemas for benchmark data
**4. `backend/models/scenario.py`** — Pydantic schemas for scenario data
**5. `backend/services/file_reader.py`** — Async functions to read JSON/JSONL from workspace
**6. `backend/api/router.py`** — Main API router, versioned under `/api/v1`
**7. `backend/api/v1/environments.py`** — `GET /environments` and `GET /environments/{env}/policies`
**8. `backend/api/v1/scenarios.py`** — `GET /scenarios/{env}?split=train|val|test`
**9. `backend/api/v1/experiments.py`** — `GET /experiments`, `GET /experiments/{id}`
**10. `backend/requirements.txt`** — `fastapi`, `uvicorn`, `pydantic`

### Frontend files to create/modify

**11. `docs/site/src/lib/components/layout/LabSidebar.svelte`** — Sidebar nav for /lab/* routes
**12. `docs/site/src/lib/components/ui/CssBarChart.svelte`** — Lightweight CSS flexbox bar charts
**13. `docs/site/src/lib/components/ui/StatusBadge.svelte`** — Pass/Fail/Blocked indicator badges
**14. `docs/site/src/lib/api/client.ts`** — Fetch wrappers using `VITE_API_BASE_URL`
**15. `docs/site/src/routes/lab/+layout.svelte`** — Layout with sidebar for lab section
**16. `docs/site/src/routes/lab/+layout.ts`** — `export const ssr = false`
**17. `docs/site/src/routes/lab/+page.svelte`** — Dashboard page: summary metrics from last experiment
**18. `docs/site/src/routes/lab/compare/+page.svelte`** — Comparison view: baseline vs manual side-by-side
**19. `docs/site/src/routes/lab/scenarios/+page.svelte`** — Scenario explorer: browse by split filter
**20. `docs/site/src/routes/lab/policies/+page.svelte`** — Policy browser: list 6 rules for expense-approval
**21. `docs/site/src/routes/lab/architecture/+page.svelte`** — Interactive governance stack diagram

## Detailed specs

### Backend API endpoints

All return JSON. All paths prefixed `/api/v1`.

**GET /environments**
```json
{
  "environments": [
    {"id": "expense-approval", "name": "Expense Approval", "description": "...", "action_count": 5, "rule_count": 6, "scenario_counts": {"train": 3, "validation": 3, "test": 4}, "status": "ready"}
  ]
}
```
Read environments by scanning `src/autoharness_lab/environments/*.py` for available classes, and `scenarios/` for counts.

**GET /environments/{env_id}/policies**
```json
{
  "environment": "expense-approval",
  "rules": [
    {"rule_id": "EXP-001", "description": "An employee cannot approve their own expenses", "priority": 1}
  ]
}
```
Read policy rules from `src/autoharness_lab/policy/expense.py` by parsing the RULE_* constants.

**GET /scenarios/{env_id}?split=train**
```json
{
  "environment": "expense-approval",
  "split": "train",
  "count": 3,
  "scenarios": [
    {
      "scenario_id": "exp-basic-001",
      "task": "alice_submit_office_supplies",
      "actor": {"user_id": "alice", "role": "employee"},
      "max_steps": 20,
      "tags": ["standard", "draft-to-approved"],
      "expense_count": 2,
      "initial_state_preview": {"expenses": {"exp-0001": {"amount": 150.0, "state": "draft", "submitter": "alice"}}}
    }
  ]
}
```
Read from `scenarios/{env_id}/{split}.jsonl`. Include a preview of initial_state but not the full object (it's large).

**GET /experiments**
```json
{
  "experiments": [
    {
      "experiment_id": "noisy-test",
      "environment": "expense-approval",
      "agent": "noisy",
      "timestamp": "2026-07-03T20:00:00",
      "metrics": {
        "task_success_rate": 0.0,
        "invalid_action_rate": 1.0,
        "composite_score": -0.5,
        "total_actions": 80
      }
    }
  ]
}
```
Read from `docs/benchmarks/expense-approval-test-*.json` files.

**GET /experiments/{experiment_id}**
Full metrics object from the JSON file.

### Backend file_reader.py

```python
async def read_jsonl(path: Path) -> list[dict]:
    """Read JSONL file, return list of parsed dicts."""

async def read_json(path: Path) -> dict:
    """Read JSON file, return parsed dict."""

def discover_environments(workspace_root: Path) -> list[dict]:
    """Scan scenarios/ dir for environment directories and their splits."""

def load_policy_rules(workspace_root: Path, env_id: str) -> list[dict]:
    """Parse policy rules from the policy module."""
```

### Frontend design

**Dark theme** (same as landing page):
- bg: #020617, text: #e2e8f0, accent: #22d3ee
- Card bg: #0f172a, border: #1e293b
- Red/rose for failures (#f43f5e), green/emerald for success (#10b981)

**LabSidebar.svelte** — Vertical nav on the left (desktop) or top (mobile):
- Dashboard, Compare, Scenarios, Policies, Architecture
- Active route highlighted with cyan left border

**Dashboard page** (`/lab`):
- Page header: "AutoHarness Lab"
- Summary cards: total scenarios, environments, experiments run
- Latest experiment results card with key metrics and a CSS bar chart

**Compare page** (`/lab/compare`):
- Two-column layout: "No Harness" vs "Manual Harness"
- Each column shows: success rate bar, invalid rate bar, composite score
- Use CssBarChart component
- Pull data from the experiments API

**Scenarios page** (`/lab/scenarios`):
- Split tabs: Train | Validation | Test
- Grid of scenario cards showing: scenario_id, task, tags, actor role
- Click to expand and see full initial_state (JSON viewer-like display)

**Policies page** (`/lab/policies`):
- Table of 6 policy rules with: rule_id, priority, description
- Subtle severity indicator (priority 1-2 = high, 3-4 = medium, 5-6 = low)

**Architecture page** (`/lab/architecture`):
- Horizontal flow diagram: [Agent] → [Harness] → [Policy] → [Environment]
- Each box clickable with description
- Pure CSS/SVG, no external diagram library

### CssBarChart.svelte props

```typescript
let { label, value, max = 1, color = "var(--cyan-400)", height = "8px" } = $props();
```

### client.ts

```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchEnvironments() { ... }
export async function fetchPolicies(envId: string) { ... }
export async function fetchScenarios(envId: string, split: string) { ... }
export async function fetchExperiments() { ... }
export async function fetchExperiment(id: string) { ... }
```

## Important constraints

### Svelte 5 runes mode
- Use `$props()` not `export let`
- Use `{@render children()}` not `<slot>`

### Link handling
- Internal links: use `{base}` from `$app/paths` for routes
- In lab routes, `base` is prepended automatically by SvelteKit

### No new npm packages
- The existing `docs/site/package.json` has svelte, sveltekit, adapter-static, vite
- Do NOT add chart.js, d3, or any charting library
- Use CSS-based charts only

### Backend requirements.txt
- `fastapi`, `uvicorn[standard]`, `pydantic`
- The backend imports from the existing `src/autoharness_lab/` package — use `sys.path.insert` or relative imports as needed

### Backend runner
The user runs the backend with:
```bash
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
```
Add a Makefile or script to make this easy.

## Verification

After writing all files:

**Backend:**
```bash
cd ~/src/enterprise-autoharness-lab
uv run pip install fastapi uvicorn pydantic
cd backend && python3 -c "from main import app; print('FastAPI app loaded OK')"
# Start server briefly to test
timeout 5 uvicorn main:app --host 0.0.0.0 --port 8000 || true
```

**Frontend:**
```bash
cd ~/src/enterprise-autoharness-lab/docs/site && npm run build
```

Both must succeed with no errors.
