<script>
  let { variant = "primary", href, target, rel, children } = $props();
</script>

<a
  class:primary={variant === "primary"}
  class:secondary={variant === "secondary"}
  class="button"
  href={href}
  {target}
  {rel}
>
  {@render children?.()}
</a>

<style>
  .button {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border-radius: 6px;
    text-decoration: none;
    transition:
      transform 0.2s ease,
      border-color 0.2s ease,
      background-color 0.2s ease,
      color 0.2s ease,
      box-shadow 0.2s ease;
  }

  .button:hover {
    transform: translateY(-1px);
  }

  .primary {
    background: var(--cyan-400);
    color: var(--slate-950);
    font-weight: 600;
    box-shadow: 0 0 30px rgba(34, 211, 238, 0.1);
  }

  .primary:hover {
    background: #67e8f9;
  }

  .secondary {
    background: transparent;
    border: 1px solid var(--slate-800);
    color: var(--slate-200);
  }

  .secondary:hover {
    border-color: var(--slate-400);
  }
</style>
