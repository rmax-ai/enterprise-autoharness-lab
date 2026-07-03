<script lang="ts">
  let { status }: { status: string } = $props();

  const normalized = $derived(status.toLowerCase());
  const tone = $derived(
    normalized === "pass" || normalized === "success" || normalized === "ready"
      ? "success"
      : normalized === "blocked" || normalized === "warning"
        ? "blocked"
        : "fail"
  );
</script>

<span class={`badge ${tone}`}>{status}</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 5.5rem;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    border: 1px solid transparent;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .success {
    color: #a7f3d0;
    background: rgba(16, 185, 129, 0.12);
    border-color: rgba(16, 185, 129, 0.32);
  }

  .fail {
    color: #fecdd3;
    background: rgba(244, 63, 94, 0.12);
    border-color: rgba(244, 63, 94, 0.32);
  }

  .blocked {
    color: #fde68a;
    background: rgba(245, 158, 11, 0.12);
    border-color: rgba(245, 158, 11, 0.32);
  }
</style>
