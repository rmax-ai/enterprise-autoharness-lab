<script lang="ts">
  const nodes = [
    {
      id: "agent",
      label: "Agent",
      subtitle: "Generates proposed actions",
      description: "LLM or scripted agent suggests the next action against the current state."
    },
    {
      id: "harness",
      label: "Harness",
      subtitle: "Predicts operational validity",
      description:
        "Read-only lab view of the deterministic validator layer. It predicts applicability but never authorizes policy."
    },
    {
      id: "policy",
      label: "Policy",
      subtitle: "Final authority",
      description:
        "Human-authored rules decide whether the action is permitted. This layer remains authoritative."
    },
    {
      id: "environment",
      label: "Environment",
      subtitle: "Mutates workflow state",
      description:
        "The workflow executes allowed actions and returns the next observation for the agent loop."
    }
  ];

  let activeId = $state("policy");
  const activeNode = $derived(nodes.find((node) => node.id === activeId) ?? nodes[0]);
</script>

<div class="page">
  <header>
    <p class="eyebrow">Governance Stack</p>
    <h1>Operational Flow</h1>
    <p class="lede">Generated code can predict. Only the policy layer can decide.</p>
  </header>

  <section class="diagram-card">
    <div class="diagram" role="list" aria-label="Governance stack">
      {#each nodes as node, index}
        <button
          type="button"
          class:active={activeId === node.id}
          onclick={() => (activeId = node.id)}
        >
          <strong>{node.label}</strong>
          <span>{node.subtitle}</span>
        </button>
        {#if index < nodes.length - 1}
          <div class="arrow" aria-hidden="true">→</div>
        {/if}
      {/each}
    </div>

    <div class="detail-panel">
      <p class="detail-kicker">{activeNode.label}</p>
      <h2>{activeNode.subtitle}</h2>
      <p>{activeNode.description}</p>
    </div>
  </section>
</div>

<style>
  .page {
    display: grid;
    gap: 1rem;
  }

  .eyebrow,
  .detail-kicker {
    color: var(--cyan-400);
    font-family: var(--font-mono);
    font-size: 0.76rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  h1,
  h2 {
    font-family: var(--font-mono);
    color: var(--slate-50);
  }

  .lede,
  .detail-panel p:last-child {
    color: var(--slate-400);
  }

  .diagram-card {
    display: grid;
    gap: 1.25rem;
    padding: 1.4rem;
    border: 1px solid var(--slate-800);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.92);
  }

  .diagram {
    display: grid;
    grid-template-columns: repeat(7, auto);
    gap: 0.75rem;
    align-items: center;
    justify-content: start;
  }

  .diagram button {
    min-width: 150px;
    padding: 1rem;
    border: 1px solid rgba(30, 41, 59, 0.9);
    border-radius: 16px;
    color: var(--slate-200);
    background:
      radial-gradient(circle at top left, rgba(34, 211, 238, 0.12), transparent 45%),
      rgba(2, 6, 23, 0.95);
    text-align: left;
    cursor: pointer;
  }

  .diagram button strong,
  .diagram button span {
    display: block;
  }

  .diagram button strong {
    margin-bottom: 0.35rem;
    font-family: var(--font-mono);
    color: var(--slate-50);
  }

  .diagram button.active {
    border-color: rgba(34, 211, 238, 0.45);
    box-shadow: 0 0 24px rgba(34, 211, 238, 0.12);
  }

  .arrow {
    color: var(--cyan-400);
    font-size: 1.8rem;
    line-height: 1;
  }

  .detail-panel {
    padding: 1rem 1.1rem;
    border-radius: 16px;
    background: rgba(2, 6, 23, 0.75);
  }

  @media (max-width: 1100px) {
    .diagram {
      grid-template-columns: 1fr;
      justify-items: stretch;
    }

    .arrow {
      justify-self: center;
      transform: rotate(90deg);
    }

    .diagram button {
      width: 100%;
    }
  }
</style>
