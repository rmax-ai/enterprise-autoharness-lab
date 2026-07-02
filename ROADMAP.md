# Roadmap

## Milestone 1 — Deterministic Research Kernel

- [ ] Common Pydantic models (Action, ExecutionResult, HarnessDecision, PolicyDecision, etc.)
- [ ] Expense-approval environment with state machine
- [ ] Expense-approval policy engine
- [ ] Noisy agent for failure generation
- [ ] Manual harness implementation
- [ ] Trace recording (AttemptRecord)
- [ ] Evaluation runner
- [ ] Deterministic tests (no external LLM required)
- [ ] CLI: `autoharness compare --environment expense-approval --conditions no-harness,manual`

## Milestone 2 — Automatic Synthesis

- [ ] Mock model client
- [ ] Initial harness generation from spec
- [ ] Counterexample extraction from traces
- [ ] Harness refinement from counterexamples
- [ ] Static validation (AST whitelist)
- [ ] Sandbox execution (subprocess)
- [ ] Candidate registry (file-system)
- [ ] Promotion logic (only when improves objective)
- [ ] CLI: `autoharness synthesize --environment expense-approval --agent noisy --iterations 5`

## Milestone 3 — Complete Evaluation

- [ ] Held-out test scenarios
- [ ] Synthesized harness comparison
- [ ] Larger-model abstraction (provider-agnostic)
- [ ] Full metric suite (task success, invalid action, false rejection, false acceptance, etc.)
- [ ] Markdown report generation
- [ ] HTML report generation (self-contained)
- [ ] CSV summary export
- [ ] Code-diff reporting between harness versions
- [ ] CLI: `autoharness report --experiment-id <id>`

## Milestone 4 — Additional Environments

- [ ] Support-ticket environment + policy engine + scenarios
- [ ] Deployment environment + policy engine + scenarios
- [ ] Cross-environment metric comparison
- [ ] CLI: `autoharness list-environments` shows all three

## Milestone 5 — Drift Experiments

- [ ] Environment mutation engine
- [ ] Before/after comparison
- [ ] Resynthesis after mutation
- [ ] Recovery metrics (counterexamples needed, iterations to recover)
- [ ] CLI: `autoharness mutate --environment expense-approval --mutation approval-threshold-change`

## Future (Post v0.1.0)

- [ ] Candidate-tree search (beam search, Thompson sampling)
- [ ] OPA/Rego policy engine integration
- [ ] Real LLM provider adapters (OpenAI, Anthropic, Google)
- [ ] Web dashboard for experiment visualization
- [ ] Parallel experiment execution
- [ ] Mutation catalog with configurable severity levels
