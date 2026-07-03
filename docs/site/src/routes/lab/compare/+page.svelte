<script lang="ts">
  import { onMount } from "svelte";
  import CssBarChart from "$lib/components/ui/CssBarChart.svelte";
  import { fetchExperiments, type Experiment } from "$lib/api/client";

  let noisy = $state<Experiment | null>(null);
  let manual = $state<Experiment | null>(null);
  let error = $state("");

  onMount(async () => {
    try {
      const { experiments } = await fetchExperiments();
      noisy = experiments.find((experiment) => experiment.agent === "noisy") ?? null;
      manual = experiments.find((experiment) => experiment.agent === "scripted") ?? null;
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "Unable to load comparison data";
    }
  });
</script>

<div class="page">
  <header>
    <p class="eyebrow">Benchmark Comparison</p>
    <h1>No Harness vs Manual Harness</h1>
    <p class="lede">
      Side-by-side metrics for the noisy baseline and the hand-written operational validator.
    </p>
  </header>

  {#if error}
    <section class="card error-card">{error}</section>
  {:else}
    <section class="compare-grid">
      <article class="card column">
        <div class="card-heading">
          <div>
            <p class="kicker">Baseline</p>
            <h2>No Harness</h2>
          </div>
          <span class="agent-chip">{noisy?.agent ?? "..."}</span>
        </div>
        {#if noisy}
          <CssBarChart label="Success rate" value={noisy.metrics.task_success_rate} color="#10b981" />
          <CssBarChart
            label="Invalid rate"
            value={noisy.metrics.invalid_action_rate}
            color="#f43f5e"
          />
          <CssBarChart
            label="Composite score"
            value={noisy.metrics.composite_score}
            max={1}
            color="#22d3ee"
          />
        {/if}
      </article>

      <article class="card column">
        <div class="card-heading">
          <div>
            <p class="kicker">Reference</p>
            <h2>Manual Harness</h2>
          </div>
          <span class="agent-chip">{manual?.agent ?? "..."}</span>
        </div>
        {#if manual}
          <CssBarChart
            label="Success rate"
            value={manual.metrics.task_success_rate}
            color="#10b981"
          />
          <CssBarChart
            label="Invalid rate"
            value={manual.metrics.invalid_action_rate}
            color="#f43f5e"
          />
          <CssBarChart
            label="Composite score"
            value={manual.metrics.composite_score}
            max={1}
            color="#22d3ee"
          />
        {/if}
      </article>
    </section>
  {/if}
</div>

<style>
  .page,
  .column {
    display: grid;
    gap: 1.25rem;
  }

  .eyebrow,
  .kicker {
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

  .lede {
    color: var(--slate-400);
  }

  .compare-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .card {
    padding: 1.4rem;
    border: 1px solid var(--slate-800);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.92);
  }

  .card-heading {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .agent-chip {
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    background: rgba(34, 211, 238, 0.08);
    color: var(--cyan-400);
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  .error-card {
    color: #fecdd3;
  }

  @media (max-width: 900px) {
    .compare-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
