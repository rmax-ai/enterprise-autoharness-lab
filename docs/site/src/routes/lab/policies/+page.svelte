<script lang="ts">
  import { onMount } from "svelte";
  import { fetchPolicies, type PolicyRule } from "$lib/api/client";

  let rules = $state<PolicyRule[]>([]);
  let error = $state("");

  function severity(priority: number): string {
    if (priority <= 2) return "high";
    if (priority <= 4) return "medium";
    return "low";
  }

  onMount(async () => {
    try {
      const response = await fetchPolicies("expense-approval");
      rules = response.rules;
    } catch (cause) {
      error = cause instanceof Error ? cause.message : "Unable to load policy rules";
    }
  });
</script>

<div class="page">
  <header>
    <p class="eyebrow">Policy Browser</p>
    <h1>Expense Approval Rules</h1>
    <p class="lede">Authoritative controls remain the final decision layer.</p>
  </header>

  {#if error}
    <section class="card error-card">{error}</section>
  {:else}
    <section class="table-card">
      <table>
        <thead>
          <tr>
            <th>Rule ID</th>
            <th>Priority</th>
            <th>Severity</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {#each rules as rule}
            <tr>
              <td>{rule.rule_id}</td>
              <td>{rule.priority}</td>
              <td>
                <span class={`severity ${severity(rule.priority)}`}>{severity(rule.priority)}</span>
              </td>
              <td>{rule.description}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}
</div>

<style>
  .page {
    display: grid;
    gap: 1rem;
  }

  .eyebrow {
    color: var(--cyan-400);
    font-family: var(--font-mono);
    font-size: 0.76rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  h1 {
    font-family: var(--font-mono);
    color: var(--slate-50);
  }

  .lede {
    color: var(--slate-400);
  }

  .table-card,
  .error-card {
    overflow-x: auto;
    padding: 1.25rem;
    border: 1px solid var(--slate-800);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.92);
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 0.95rem 0.75rem;
    border-bottom: 1px solid rgba(30, 41, 59, 0.9);
    text-align: left;
  }

  th {
    color: var(--slate-400);
    font-family: var(--font-mono);
    font-size: 0.76rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  td {
    color: var(--slate-200);
  }

  .severity {
    display: inline-flex;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    text-transform: capitalize;
  }

  .severity.high {
    color: #fecdd3;
    background: rgba(244, 63, 94, 0.12);
  }

  .severity.medium {
    color: #fde68a;
    background: rgba(245, 158, 11, 0.12);
  }

  .severity.low {
    color: #bfdbfe;
    background: rgba(59, 130, 246, 0.12);
  }

  .error-card {
    color: #fecdd3;
  }
</style>
