<script lang="ts">
  import { onMount } from "svelte";
  import { fetchScenarios, type Scenario } from "$lib/api/client";

  const tabs = [
    { id: "train", label: "Train" },
    { id: "val", label: "Validation" },
    { id: "test", label: "Test" }
  ];

  let split = $state("train");
  let scenarios = $state<Scenario[]>([]);
  let count = $state(0);
  let expandedId = $state<string | null>(null);
  let error = $state("");
  let loading = $state(true);

  async function load(activeSplit: string): Promise<void> {
    loading = true;
    split = activeSplit;
    expandedId = null;
    error = "";
    try {
      const response = await fetchScenarios("expense-approval", activeSplit);
      scenarios = response.scenarios;
      count = response.count;
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "Unable to load scenarios";
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    await load(split);
  });
</script>

<div class="page">
  <header class="header-row">
    <div>
      <p class="eyebrow">Scenario Explorer</p>
      <h1>Expense Approval Corpus</h1>
    </div>
    <div class="count-chip">{count} scenarios</div>
  </header>

  <div class="tab-row" role="tablist" aria-label="Scenario split">
    {#each tabs as tab}
      <button
        type="button"
        class:active={split === tab.id}
        onclick={() => load(tab.id)}
      >
        {tab.label}
      </button>
    {/each}
  </div>

  {#if error}
    <section class="card error-card">{error}</section>
  {:else if loading}
    <section class="card muted">Loading scenarios…</section>
  {:else}
    <section class="scenario-grid">
      {#each scenarios as scenario}
        <article class="card scenario-card">
          <div class="scenario-top">
            <div>
              <h2>{scenario.scenario_id}</h2>
              <p class="task">{scenario.task}</p>
            </div>
            <button
              type="button"
              class="toggle"
              onclick={() => (expandedId = expandedId === scenario.scenario_id ? null : scenario.scenario_id)}
            >
              {expandedId === scenario.scenario_id ? "Hide state" : "Expand"}
            </button>
          </div>

          <div class="meta-grid">
            <span>Role: {scenario.actor.role}</span>
            <span>User: {scenario.actor.user_id}</span>
            <span>Expenses: {scenario.expense_count}</span>
            <span>Max steps: {scenario.max_steps}</span>
          </div>

          <div class="tags">
            {#each scenario.tags as tag}
              <span>{tag}</span>
            {/each}
          </div>

          <pre class="preview">{JSON.stringify(scenario.initial_state_preview, null, 2)}</pre>

          {#if expandedId === scenario.scenario_id}
            <pre class="full-state">{JSON.stringify(scenario.initial_state, null, 2)}</pre>
          {/if}
        </article>
      {/each}
    </section>
  {/if}
</div>

<style>
  .page,
  .scenario-card {
    display: grid;
    gap: 1rem;
  }

  .header-row,
  .scenario-top {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .eyebrow {
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

  .count-chip,
  .toggle,
  .tab-row button {
    font-family: var(--font-mono);
    font-size: 0.78rem;
  }

  .count-chip {
    padding: 0.45rem 0.8rem;
    border-radius: 999px;
    background: rgba(34, 211, 238, 0.08);
    color: var(--cyan-400);
  }

  .tab-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
  }

  .tab-row button,
  .toggle {
    padding: 0.55rem 0.9rem;
    border: 1px solid var(--slate-800);
    border-radius: 999px;
    color: var(--slate-200);
    background: rgba(15, 23, 42, 0.92);
    cursor: pointer;
  }

  .tab-row button.active {
    border-color: rgba(34, 211, 238, 0.4);
    color: var(--slate-50);
    background: rgba(34, 211, 238, 0.08);
  }

  .scenario-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .card {
    padding: 1.25rem;
    border: 1px solid var(--slate-800);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.92);
  }

  .task,
  .meta-grid {
    color: var(--slate-400);
  }

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.4rem 1rem;
    font-size: 0.88rem;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .tags span {
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    background: rgba(30, 41, 59, 0.9);
    color: var(--slate-200);
    font-size: 0.78rem;
  }

  .preview,
  .full-state {
    overflow-x: auto;
    padding: 0.9rem;
    border-radius: 14px;
    background: #020617;
    color: #cbd5e1;
    font-size: 0.82rem;
  }

  .full-state {
    border: 1px solid rgba(34, 211, 238, 0.2);
  }

  .muted,
  .error-card {
    color: var(--slate-400);
  }

  .error-card {
    color: #fecdd3;
  }

  @media (max-width: 900px) {
    .scenario-grid,
    .meta-grid {
      grid-template-columns: 1fr;
    }

    .header-row,
    .scenario-top {
      flex-direction: column;
    }
  }
</style>
