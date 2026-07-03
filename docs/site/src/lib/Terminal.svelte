<div class="terminal">
  <div class="terminal-bar">
    <div class="dots" aria-hidden="true">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
    </div>
    <span class="title">Terminal — autoharness</span>
  </div>

  <pre class="terminal-body"><code><span class="command">$ git clone https://github.com/rmax-ai/enterprise-autoharness-lab.git</span>
<span class="command">$ cd enterprise-autoharness-lab &amp;&amp; uv sync --extra dev</span>
<span class="command">$ uv run autoharness compare -e expense-approval -c no-harness,manual -d test</span>

<span class="output">&gt; Loaded 4 scenarios from scenarios/expense-approval/test.jsonl
&gt;
&gt;                       Comparison: expense-approval (test)
&gt; ┌────────────┬──────────┬──────────┬──────────┬───────────┐
&gt; │ Condition  │ Success  │ Invalid  │ Policy   │ Composite │
&gt; ├────────────┼──────────┼──────────┼──────────┼───────────┤
&gt; │ no-harness │    0.0%  │  100.0%  │   0.0%   │    -0.50  │
&gt; │ manual     │    0.0%  │  100.0%  │   0.0%   │    -0.50  │
&gt; └────────────┴──────────┴──────────┴──────────┴───────────┘</span>

<span class="command">$ uv run autoharness run-baseline -e expense-approval -a scripted</span>

<span class="output">&gt; &#123;&quot;task_success_rate&quot;: 1.0, &quot;invalid_action_rate&quot;: 0.0,</span>
<span class="output">&gt;  &quot;composite_score&quot;: 1.0, &quot;total_actions&quot;: 4&#125;</span></code></pre>
</div>

<style>
  .terminal {
    background: var(--slate-900);
    border: 1px solid var(--slate-800);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 0 30px rgba(34, 211, 238, 0.1);
  }

  .terminal-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--slate-800);
    background: rgba(15, 23, 42, 0.95);
  }

  .dots {
    display: flex;
    gap: 0.5rem;
  }

  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }

  .red {
    background: #ff5f56;
  }

  .yellow {
    background: #ffbd2e;
  }

  .green {
    background: #27c93f;
  }

  .title {
    color: var(--slate-400);
    font-family: var(--font-mono);
    font-size: 0.85rem;
  }

  .terminal-body {
    margin: 0;
    padding: 1.5rem;
    overflow-x: auto;
    font-family: var(--font-mono);
    font-size: 0.95rem;
    line-height: 1.7;
    white-space: pre;
  }

  .command {
    color: var(--slate-50);
  }

  .output {
    color: var(--slate-400);
  }
</style>
