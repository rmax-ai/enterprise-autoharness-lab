You are reviewing an implementation plan for adding a Gemini 2.5 Flash agent to this project.

## Your task

Read the plan at `docs/plans/gemini-agent-plan.md`. Then read these existing files for context:

- `src/autoharness_lab/models.py` — the Agent protocol and ModelClient protocol
- `src/autoharness_lab/agents/scripted.py` — existing agent implementation pattern
- `src/autoharness_lab/agents/noisy.py` — existing agent implementation pattern
- `src/autoharness_lab/cli.py` — how agents are registered and used
- `src/autoharness_lab/evaluation/runner.py` — how agent.propose_action is called
- `AGENTS.md` — project conventions

## What to validate

1. **Architecture fit** — Does the plan follow the project's protocols and conventions? Any violations of AGENTS.md non-negotiables?

2. **Completeness** — Are there missing files, edge cases, or integration points the plan doesn't cover?

3. **Prompt quality** — Is the system prompt strategy sound? The prompt needs to encode expense approval domain rules well enough that Gemini produces correct actions.

4. **Risk assessment** — Any risks the plan missed? Especially around google-genai SDK version, structured output reliability, token limits.

5. **Test coverage** — Are the test cases sufficient? What's missing?

6. **CLI integration** — Will `autoharness compare -e expense-approval -c gemini` actually work after implementation?

## Deliverable

At the END of your review, write a findings file at `docs/plans/gemini-agent-plan-review.md` with:

- **Gaps found** — things the plan missed entirely
- **Concerns** — things in the plan that may not work as described  
- **Improvements** — concrete suggestions to strengthen the plan
- **Verdict** — PROCEED / PROCEED-WITH-FIXES / BLOCKED

Do NOT implement anything. Only review the plan. Read existing files first.
