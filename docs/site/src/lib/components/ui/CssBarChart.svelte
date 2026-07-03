<script lang="ts">
  let {
    label,
    value,
    max = 1,
    color = "var(--cyan-400)",
    height = "8px"
  }: {
    label: string;
    value: number;
    max?: number;
    color?: string;
    height?: string;
  } = $props();

  const safeMax = $derived(max <= 0 ? 1 : max);
  const ratio = $derived(Math.max(0, Math.min(value / safeMax, 1)));
</script>

<div class="chart">
  <div class="chart-header">
    <span>{label}</span>
    <strong>{value.toFixed(2)}</strong>
  </div>
  <div class="track" style={`height:${height};`}>
    <div class="fill" style={`width:${ratio * 100}%; background:${color};`}></div>
  </div>
</div>

<style>
  .chart {
    display: grid;
    gap: 0.45rem;
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-size: 0.88rem;
    color: var(--slate-300, var(--slate-200));
  }

  strong {
    color: var(--slate-50);
    font-family: var(--font-mono);
  }

  .track {
    overflow: hidden;
    border-radius: 999px;
    background: rgba(30, 41, 59, 0.9);
  }

  .fill {
    height: 100%;
    border-radius: inherit;
    box-shadow: 0 0 18px color-mix(in srgb, currentColor 35%, transparent);
  }
</style>
