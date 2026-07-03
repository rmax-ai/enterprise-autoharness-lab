<script>
  import Button from "$lib/Button.svelte";
  import DataTable from "$lib/DataTable.svelte";
  import GovernanceStack from "$lib/GovernanceStack.svelte";
  import Terminal from "$lib/Terminal.svelte";

  const githubHref = "https://github.com/rmax-ai/enterprise-autoharness-lab";
  const paperHref = "https://arxiv.org/abs/2603.03329";

  const features = [
    {
      title: "AST-Validated Sandboxing",
      description:
        "Generated code is statically analyzed to block dangerous operations before runtime."
    },
    {
      title: "Counterexample Learning",
      description:
        "Every invalid action becomes structured training data. The harness writes its own test suite."
    },
    {
      title: "Environment Drift Detection",
      description:
        "When business rules change, the system detects drift and re-synthesizes the harness automatically."
    },
    {
      title: "100% Reproducible",
      description:
        "No external LLMs required to run evaluations. Mock model clients ensure full determinism."
    }
  ];

  const workflows = [
    {
      icon: "💰",
      title: "Expense Approval",
      actions: "submit, approve, reject, escalate",
      catches: ["self-approvals", "out-of-policy amounts", "missing receipts"]
    },
    {
      icon: "🎫",
      title: "Customer Support",
      actions: "assign, prioritize, resolve, refund",
      catches: ["SLA violations", "unauthorized refunds", "invalid state transitions"]
    },
    {
      icon: "🚀",
      title: "Software Deployment",
      actions: "create, approve, start, verify, rollback",
      catches: ["production freezes", "unauthorized approvals", "rollback-tight scenarios"]
    }
  ];
</script>

<svelte:head>
  <title>Enterprise AutoHarness Lab</title>
</svelte:head>

<section class="section hero">
  <p class="eyebrow">Open-Source Research Project</p>
  <h1>Deterministic Guardrails for Enterprise AI.</h1>
  <p class="hero-copy">
    Stop relying on prompt engineering for safety. AutoHarness uses LLMs to synthesize
    deterministic validation code. The AI writes the harness, the sandbox runs it, and your
    policy engine retains ultimate authority.
  </p>
  <div class="button-row">
    <Button href={githubHref} target="_blank" rel="noopener noreferrer">View on GitHub</Button>
    <Button variant="secondary" href={paperHref} target="_blank" rel="noopener noreferrer">
      Read the Research Paper
    </Button>
  </div>
  <p class="attribution">
    Based on <a href={paperHref} target="_blank" rel="noopener noreferrer">AutoHarness</a> (arXiv:2603.03329)
    — applied here to enterprise AI workflows.
  </p>
  <div class="hero-stats" aria-label="project metrics">
    <div class="stat-card">
      <span class="stat-value">175</span>
      <span class="stat-label">Tests across end-to-end scenarios</span>
    </div>
    <div class="stat-card">
      <span class="stat-value">3</span>
      <span class="stat-label">Enterprise workflow environments</span>
    </div>
    <div class="stat-card">
      <span class="stat-value">CLI</span>
      <span class="stat-label">compare, synthesize, report, mutate</span>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-copy">
    <p class="eyebrow">The Governance Stack</p>
    <h2>Generated code. Not generated decisions.</h2>
    <p>
      LLMs are excellent at writing code, but terrible at enforcing rules. AutoHarness physically
      separates generation from execution. The LLM synthesizes an AST-validated Python harness that
      runs in a sandbox. The policy engine always has the final say.
    </p>
  </div>
  <GovernanceStack />
</section>

<section class="section">
  <div class="section-copy">
    <p class="eyebrow">The Proof</p>
    <h2>Production-Grade Convergence.</h2>
    <p>
      Tested across 175 scenarios and three enterprise environments. The synthesis loop
      consistently generates harnesses that outperform naked agents and rival human-authored
      rules.
    </p>
  </div>
  <DataTable />
</section>

<section class="section">
  <div class="section-copy">
    <p class="eyebrow">Feature Grid</p>
    <h2>Failure-Driven Refinement.</h2>
  </div>
  <div class="feature-grid">
    {#each features as feature}
      <article class="card">
        <h3>{feature.title}</h3>
        <p>{feature.description}</p>
      </article>
    {/each}
  </div>
</section>

<section class="section">
  <div class="section-copy">
    <p class="eyebrow">Enterprise Workflows</p>
    <h2>Built for High-Stakes Environments.</h2>
  </div>
  <div class="workflow-grid">
    {#each workflows as workflow}
      <article class="card workflow-card">
        <div class="workflow-header">
          <span class="workflow-icon" aria-hidden="true">{workflow.icon}</span>
          <h3>{workflow.title}</h3>
        </div>
        <p class="meta-label">Actions</p>
        <p class="meta-value">{workflow.actions}</p>
        <p class="meta-label">Catches</p>
        <div class="tags">
          {#each workflow.catches as item}
            <span class="tag">{item}</span>
          {/each}
        </div>
      </article>
    {/each}
  </div>
</section>

<section class="section">
  <div class="section-copy">
    <p class="eyebrow">CLI Demo</p>
    <h2>One Command to Synthesis.</h2>
  </div>
  <Terminal />
</section>

<section class="section cta">
  <div class="cta-card">
    <p class="eyebrow">Final CTA</p>
    <h2>Ready to put guardrails on your AI agents?</h2>
    <div class="button-row">
      <Button href={githubHref} target="_blank" rel="noopener noreferrer">View on GitHub</Button>
      <Button variant="secondary" href={paperHref} target="_blank" rel="noopener noreferrer">
        Read the Research Paper
      </Button>
    </div>
  </div>
</section>

<style>
  .section {
    max-width: 1000px;
    margin: 0 auto;
    padding: 5rem 2rem;
  }

  .hero {
    padding-top: 6rem;
    padding-bottom: 6rem;
    text-align: center;
  }

  .eyebrow {
    margin-bottom: 1rem;
    color: var(--cyan-400);
    font-family: var(--font-mono);
    font-size: 0.85rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  h1,
  h2,
  h3 {
    font-family: var(--font-mono);
    color: var(--slate-50);
    line-height: 1.05;
  }

  h1 {
    max-width: 12ch;
    margin: 0 auto 1.5rem;
    font-size: clamp(3.5rem, 8vw, 5rem);
    letter-spacing: -0.04em;
  }

  h2 {
    margin-bottom: 1rem;
    font-size: clamp(2.2rem, 4vw, 3rem);
  }

  h3 {
    margin-bottom: 0.75rem;
    font-size: 1.3rem;
  }

  p {
    color: var(--slate-400);
    font-size: 1rem;
  }

  .hero-copy {
    max-width: 760px;
    margin: 0 auto;
    font-size: 1.15rem;
  }

  .attribution {
    margin-top: 1rem;
    color: var(--slate-400);
    font-size: 0.8rem;
    font-family: var(--font-mono);
  }

  .attribution a {
    color: var(--cyan-400);
    text-decoration: none;
  }

  .attribution a:hover {
    text-decoration: underline;
  }

  .button-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 1rem;
    margin-top: 2rem;
  }

  .hero-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    margin-top: 3rem;
  }

  .stat-card,
  .card,
  .cta-card {
    background: var(--slate-900);
    border: 1px solid var(--slate-800);
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 0 30px rgba(34, 211, 238, 0.1);
  }

  .stat-card {
    text-align: left;
  }

  .stat-value {
    display: block;
    margin-bottom: 0.4rem;
    color: var(--slate-50);
    font-family: var(--font-mono);
    font-size: 1.6rem;
  }

  .section-copy {
    max-width: 760px;
    margin-bottom: 2rem;
  }

  .feature-grid,
  .workflow-grid {
    display: grid;
    gap: 1.25rem;
  }

  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workflow-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .card p:last-child {
    margin-bottom: 0;
  }

  .workflow-card {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }

  .workflow-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
  }

  .workflow-header h3 {
    margin: 0;
  }

  .workflow-icon {
    font-size: 1.5rem;
  }

  .meta-label {
    color: var(--slate-400);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .meta-value {
    color: var(--slate-200);
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
  }

  .tag {
    background: rgba(34, 211, 238, 0.1);
    color: var(--cyan-400);
    border-radius: 999px;
    padding: 0.2rem 0.6rem;
    font-size: 0.8rem;
  }

  .cta {
    padding-bottom: 6rem;
  }

  .cta-card {
    text-align: center;
  }

  @media (max-width: 900px) {
    .hero-stats,
    .workflow-grid {
      grid-template-columns: 1fr;
    }

    .feature-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .section {
      padding: 4rem 1.25rem;
    }

    h1 {
      font-size: clamp(3.5rem, 16vw, 4.25rem);
    }

    .stat-card,
    .card,
    .cta-card {
      padding: 1.5rem;
    }
  }
</style>
