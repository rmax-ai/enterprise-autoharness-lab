<script lang="ts">
  import { base } from "$app/paths";
  import { page } from "$app/state";

  const items = [
    { label: "Dashboard", path: "/lab" },
    { label: "Compare", path: "/lab/compare" },
    { label: "Scenarios", path: "/lab/scenarios" },
    { label: "Policies", path: "/lab/policies" },
    { label: "Architecture", path: "/lab/architecture" }
  ];

  function isActive(path: string): boolean {
    const href = `${base}${path}`;
    return path === "/lab" ? page.url.pathname === href : page.url.pathname.startsWith(href);
  }
</script>

<nav class="sidebar" aria-label="Lab navigation">
  <div class="sidebar-header">
    <p class="eyebrow">Read-Only Lab</p>
    <h2>Foundation Layer</h2>
  </div>

  <div class="nav-list">
    {#each items as item}
      <a href={`${base}${item.path}`} class:active={isActive(item.path)}>
        {item.label}
      </a>
    {/each}
  </div>
</nav>

<style>
  .sidebar {
    display: grid;
    gap: 1.5rem;
    padding: 1.25rem;
    border: 1px solid var(--slate-800);
    border-radius: 18px;
    background:
      linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(2, 6, 23, 0.94)),
      var(--slate-900);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  .sidebar-header h2 {
    font-family: var(--font-mono);
    font-size: 1.2rem;
    color: var(--slate-50);
  }

  .eyebrow {
    margin-bottom: 0.4rem;
    color: var(--cyan-400);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .nav-list {
    display: grid;
    gap: 0.35rem;
  }

  .nav-list a {
    padding: 0.8rem 0.95rem;
    border-left: 3px solid transparent;
    border-radius: 12px;
    color: var(--slate-300, var(--slate-200));
    text-decoration: none;
    background: rgba(15, 23, 42, 0.55);
    transition:
      border-color 0.2s ease,
      color 0.2s ease,
      background 0.2s ease;
  }

  .nav-list a:hover {
    color: var(--slate-50);
    background: rgba(30, 41, 59, 0.8);
  }

  .nav-list a.active {
    border-left-color: var(--cyan-400);
    color: var(--slate-50);
    background: rgba(34, 211, 238, 0.08);
  }

  @media (max-width: 900px) {
    .nav-list {
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    }

    .nav-list a {
      border-left: 0;
      border-top: 3px solid transparent;
    }

    .nav-list a.active {
      border-top-color: var(--cyan-400);
    }
  }
</style>
