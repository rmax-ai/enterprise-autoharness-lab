<script lang="ts">
  import { onMount } from "svelte";
  import CssBarChart from "$lib/components/ui/CssBarChart.svelte";
  import StatusBadge from "$lib/components/ui/StatusBadge.svelte";
  import { fetchEnvironments, fetchExperiments, type Environment, type Experiment } from "$lib/api/client";

  let environments = $state<Environment[]>([]);
  let experiments = $state<Experiment[]>([]);
  let error = $state("");
  let loading = $state(true);

  const totalScenarios = $derived(
    environments.reduce(
      (sum, environment) =>
        sum +
        environment.scenario_counts.train +
        environment.scenario_counts.validation +
        environment.scenario_counts.test,
      0
    )
  );
  const latestExperiment = $derived(experiments[0] ?? null);

  onMount(async () => {
    try {
      const [envResponse, experimentResponse] = await Promise.all([
        fetchEnvironments(),
        fetchExperiments()
      ]);
      environments = envResponse.environments;
      experiments = experimentResponse.experiments;
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "Unable to load lab data";
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>AutoHarness Lab</title>
</svelte:head>

<div class="page">
  <header class="page-header">
    <div>
      <p class="eyebrow">Foundation & Read-Only State</p>
      <h1>AutoHarness Lab</h1>
      <p class="lede">
        A browser view over the benchmark artifacts, scenario corpus, and governance stack.
      </p>
    </div>
    <StatusBadge status={loading ? "Blocked" : "Ready"} />
  </header>

  {#if error}
    <section class="card error-card">{error}</section>
  {:else}
    <section class="summary-grid">
      <article class="card stat-card">
        <span class="stat-label">Total scenarios</span>
        <strong>{totalScenarios}</strong>
      </article>
      <article class="card stat-card">
        <span class="stat-label">Environments</span>
        <strong>{environments.length}</strong>
      </article>
      <article class="card stat-card">
        <span class="stat-label">Experiments run</span>
        <strong>{experiments.length}</strong>
      </article>
    </section>

    <section class="card latest-card">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Latest experiment</p>
          <h2>{latestExperiment?.experiment_id ?? "Waiting for data"}</h2>
        </div>
        {#if latestExperiment}
          <StatusBadge
            status={latestExperiment.metrics.task_success_rate >= 0.5 ? "Pass" : "Fail"}
          />
        {/if}
      </div>

      {#if latestExperiment}
        <div class="experiment-meta">
          <span>{latestExperiment.environment}</span>
          <span>{latestExperiment.agent}</span>
          <span>{latestExperiment.timestamp}</span>
        </div>
        <div class="chart-grid">
          <CssBarChart
            label="Task success"
            value={latestExperiment.metrics.task_success_rate}
            color="#10b981"
          />
          <CssBarChart
            label="Invalid action rate"
            value={latestExperiment.metrics.invalid_action_rate}
            color="#f43f5e"
          />
          <CssBarChart
            label="Composite score"
            value={latestExperiment.metrics.composite_score}
            max={1}
            color="#22d3ee"
          />
        </div>
        <div class="totals-row">
          <span>Total actions</span>
          <strong>{latestExperiment.metrics.total_actions}</strong>
        </div>
      {:else if loading}
        <p class="placeholder">Loading experiment summary…</p>
      {:else}
        <p class="placeholder">No experiment artifacts found.</p>
      {/if}
    </section>
  {/if}
</div>

<style>
  .page {
    display: grid;
    gap: 1.5rem;
  }

  .page-header,
  .section-heading,
  .experiment-meta,
  .totals-row {
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

  h1 {
    font-size: clamp(2.4rem, 5vw, 3.4rem);
    line-height: 1.05;
  }

  .lede,
  .experiment-meta,
  .placeholder {
    color: var(--slate-400);
  }

  .card {
    padding: 1.4rem;
    border: 1px solid var(--slate-800);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.92);
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
  }

  .stat-card strong {
    margin-top: 0.45rem;
    display: block;
    font-family: var(--font-mono);
    font-size: 2.4rem;
    color: var(--slate-50);
  }

  .stat-label {
    color: var(--slate-400);
    font-size: 0.88rem;
  }

  .latest-card {
    display: grid;
    gap: 1.25rem;
  }

  .experiment-meta {
    flex-wrap: wrap;
    font-size: 0.88rem;
  }

  .chart-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
  }

  .totals-row strong {
    color: var(--slate-50);
    font-family: var(--font-mono);
  }

  .error-card {
    color: #fecdd3;
    border-color: rgba(244, 63, 94, 0.28);
  }

  @media (max-width: 900px) {
    .summary-grid,
    .chart-grid {
      grid-template-columns: 1fr;
    }

    .page-header,
    .section-heading,
    .totals-row {
      flex-direction: column;
    }
  }
</style>
