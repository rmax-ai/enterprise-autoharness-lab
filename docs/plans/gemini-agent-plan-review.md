## Gaps found

- The plan claims `autoharness compare -e expense-approval -c gemini` will work, but `compare` treats `-c/--conditions` as comparison conditions, not agent names. Today it only recognizes `no-harness`, `manual`, `generated`, and `large-model` in [src/autoharness_lab/cli.py](/home/rmax-10/src/enterprise-autoharness-lab/src/autoharness_lab/cli.py:107). Adding `gemini` to `_get_agent()` only makes `run-baseline -a gemini` possible.
- The prompt strategy depends on policy-relevant actor data, but the `Agent` protocol and runner do not pass actor context into `propose_action()`. `propose_action()` only receives `task`, `observation`, and `available_actions` in [src/autoharness_lab/models.py](/home/rmax-10/src/enterprise-autoharness-lab/src/autoharness_lab/models.py:209) and [src/autoharness_lab/evaluation/runner.py](/home/rmax-10/src/enterprise-autoharness-lab/src/autoharness_lab/evaluation/runner.py:182). That means the Gemini agent cannot reliably reason about self-approval, role, or approval limits, which are enforced by policy in [src/autoharness_lab/policy/expense.py](/home/rmax-10/src/enterprise-autoharness-lab/src/autoharness_lab/policy/expense.py:95).
- The proposed prompt file location conflicts with project conventions. AGENTS requires LLM prompts under `src/autoharness_lab/synthesis/prompts/` in versioned files with provenance hashes in [AGENTS.md](/home/rmax-10/src/enterprise-autoharness-lab/AGENTS.md:64). The plan puts the prompt in `src/autoharness_lab/agents/prompts/expense_agent_system.txt`.
- The plan says the prompt will be hashed for provenance, but it does not describe any plumbing for storing prompt version/hash, model identifier, or generation settings for reproducibility. AGENTS requires experiments to be reproducible from prompt version, model identifier, and code hash in [AGENTS.md](/home/rmax-10/src/enterprise-autoharness-lab/AGENTS.md:27). The current experiment records do not capture Gemini-specific metadata.
- The plan introduces `src/autoharness_lab/model_clients/__init__.py` as “re-export ModelClient + registry”, but no registry exists in the current design and no registry changes are described elsewhere. That file appears unnecessary or underspecified.
- Test coverage is incomplete against project requirements. AGENTS explicitly calls for at least one end-to-end test without an external LLM in [AGENTS.md](/home/rmax-10/src/enterprise-autoharness-lab/AGENTS.md:53). The plan adds unit tests and a live integration test, but no new mock-client end-to-end experiment coverage for Gemini.

## Concerns

- The prompt summary is too weak for the actual expense domain. It omits actor role and approval limit checks from policy, exact threshold behavior, escalation conditions, and the fact that `request_receipt` immediately attaches a receipt in the environment rather than sending a request. Those semantics are visible in [src/autoharness_lab/environments/expense_approval.py](/home/rmax-10/src/enterprise-autoharness-lab/src/autoharness_lab/environments/expense_approval.py:244) and [src/autoharness_lab/policy/expense.py](/home/rmax-10/src/enterprise-autoharness-lab/src/autoharness_lab/policy/expense.py:116).
- The fallback action is described as `Action(type="submit_expense", arguments={"expense_id": "none"})`. In this environment that is not a no-op; it is an invalid action that will repeatedly fail in the runner loop. It is a brittle failure mode, not graceful degradation.
- `google-genai>=1.0` is too loose given the stated concern about SDK churn. The mitigation table says to pin a known working version, but the dependency line does not do that.
- Putting `google-genai` in core dependencies and likely importing Gemini code from the CLI path increases coupling to one provider. That does not violate the `ModelClient` protocol by itself, but it weakens the provider-agnostic goal in [AGENTS.md](/home/rmax-10/src/enterprise-autoharness-lab/AGENTS.md:31). A lazy import or optional extra would be safer.
- The plan assumes native structured output will simply deserialize into a Pydantic model. In practice, Gemini structured output still needs explicit validation for missing fields, extra fields, malformed nested arguments, refusals, empty candidates, and SDK response-shape drift. The current plan only mentions invalid action type and malformed JSON.
- Token logging and token counting are called out, but the `ModelClient` protocol does not expose usage metadata, and the plan does not describe where those metrics would live. That part of the plan is underspecified.
- The public signatures shown in the plan continue the existing `dict[str, Any]` pattern. That matches current protocols, but it does not move the codebase toward the AGENTS preference for typed public interfaces in [AGENTS.md](/home/rmax-10/src/enterprise-autoharness-lab/AGENTS.md:79).
- Live integration tests against Gemini will be flaky and non-deterministic. They should be opt-in, clearly marked, and excluded from default CI. The plan says “integration” but does not define the execution policy.

## Improvements

- Split CLI goals clearly:
  - Add `gemini` to `_get_agent()` so `autoharness run-baseline -e expense-approval -a gemini` works.
  - Separately decide how `compare` should support agent selection. That likely requires a new option such as `--agent` or a new condition that explicitly maps to `GeminiAgent`.
- Fix the context contract before relying on prompt quality. The clean options are:
  - Extend the `Agent` protocol and `run_experiment()` to pass actor context.
  - Or include actor context in the observation snapshot before the agent is called.
  Without this, the Gemini agent cannot reliably satisfy the expense policy.
- Move the prompt into `src/autoharness_lab/synthesis/prompts/` and version it explicitly, for example `expense_agent_system_v1.txt`. Add a small helper that loads the file and computes a stable hash so the run can record prompt provenance.
- Add a concrete reproducibility plan. At minimum, capture model name, SDK version, prompt hash, and generation config for each Gemini run, either in trace metadata or a run manifest.
- Tighten the Gemini dependency to a tested range or exact version instead of `>=1.0`. The plan should name the version it was validated against.
- Make the structured output contract stricter:
  - Define a typed response model for allowed arguments.
  - Validate `expense_id` existence.
  - Inject `actor` where required for `approve_expense`, `reject_expense`, and `escalate_expense`.
  - Handle refusals, empty responses, and schema mismatch explicitly.
- Replace the invalid fallback action with a deterministic repair strategy. For example, choose a valid action only when one can be derived from the observation; otherwise fail closed in a clearly testable way instead of emitting `expense_id="none"`.
- Add missing tests:
  - End-to-end mock `GeminiAgent` experiment in `tests/end_to_end/`.
  - CLI smoke tests for `_get_agent("gemini")` and command behavior.
  - Prompt-loading and prompt-hash tests.
  - Structured-output edge cases: refusal, empty payload, extra fields, wrong types, missing `actor` injection.
  - Policy-sensitive behavior tests once actor context is available: self-approval denial avoidance, over-limit escalation, receipt-required repair.

## Verdict

PROCEED-WITH-FIXES

The plan is directionally compatible with the `Agent` and `ModelClient` protocols, but it misses two blocking design details for a credible implementation: prompt/versioning provenance is not wired to project conventions, and the agent lacks actor context needed to make expense-policy-aware decisions. The CLI claim for `compare -c gemini` is also incorrect as written. Once those are fixed, the remaining work looks straightforward.
