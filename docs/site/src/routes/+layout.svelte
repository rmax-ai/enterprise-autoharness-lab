<script>
  import { base } from "$app/paths";

  let { children } = $props();
</script>

<svelte:head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="dark" />
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>" />
</svelte:head>

<div class="layout">
  <nav class="top-nav">
    <a href={base + "/"} class="logo">AutoHarness Lab</a>
    <div class="nav-links">
      <a href="https://github.com/rmax-ai/enterprise-autoharness-lab" target="_blank" rel="noopener">GitHub</a>
      <a href="https://arxiv.org/abs/2603.03329" target="_blank" rel="noopener">Paper</a>
    </div>
  </nav>
  <main>
    {@render children()}
  </main>
  <footer>
    <span>MIT Licensed · <a href="https://github.com/rmax-ai/enterprise-autoharness-lab">rmax-ai/enterprise-autoharness-lab</a></span>
  </footer>
</div>

<style>
  :root {
    --slate-50: #f8fafc;
    --slate-200: #e2e8f0;
    --slate-400: #94a3b8;
    --slate-800: #1e293b;
    --slate-900: #0f172a;
    --slate-950: #020617;
    --cyan-400: #22d3ee;
    --cyan-500: #06b6d4;
    --cyan-900: #164e63;
    --font-sans: system-ui, -apple-system, sans-serif;
    --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    background-color: var(--slate-950);
    color: var(--slate-200);
    font-family: var(--font-sans);
    line-height: 1.6;
  }

  .layout {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background: radial-gradient(circle at 50% -20%, var(--cyan-900) 0%, var(--slate-950) 40%);
  }

  .top-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 2rem;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }

  .logo {
    font-weight: 700;
    font-size: 1.125rem;
    color: var(--slate-50);
    text-decoration: none;
    font-family: var(--font-mono);
  }

  .nav-links {
    display: flex;
    gap: 1.5rem;
  }

  .nav-links a {
    color: var(--slate-400);
    text-decoration: none;
    font-size: 0.875rem;
    transition: color 0.2s;
  }

  .nav-links a:hover { color: var(--slate-200); }

  main {
    flex: 1;
  }

  footer {
    text-align: center;
    padding: 3rem 2rem;
    color: var(--slate-400);
    font-size: 0.8rem;
    border-top: 1px solid var(--slate-800);
  }

  footer a { color: var(--slate-400); }
  footer a:hover { color: var(--slate-200); }
</style>
