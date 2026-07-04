<div class="terminal">
  <div class="terminal-bar">
    <div class="dots" aria-hidden="true">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
    </div>
    <span class="title">Terminal — expense-approval</span>
  </div>

  <pre class="terminal-body"><code><span class="command">$ uv run autoharness compare -e expense-approval -c no-harness,manual -d test</span>

<span class="output">&gt; Loaded 9 scenarios from scenarios/expense-approval/test.jsonl
&gt;
&gt;                       Comparison: expense-approval (test)
&gt; ┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
&gt; ┃            ┃              ┃              ┃ Policy      ┃           ┃         ┃
&gt; ┃ Condition  ┃ Success Rate ┃ Invalid Rate ┃ Denial      ┃ Composite ┃ Actions ┃
&gt; ┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
&gt; │ no-harness │ 0.0%         │ 100.0%       │ 0.0%        │ -0.500    │ 180     │
&gt; │ manual     │ 0.0%         │ 100.0%       │ 0.0%        │ -0.500    │ 180     │
&gt; └────────────┴──────────────┴──────────────┴─────────────┴───────────┴─────────┘</span>

<span class="command">$ uv run autoharness run-baseline -e expense-approval -a scripted -d test</span>

<span class="output">&gt; &#123;
&gt;   "task_success_rate": 1.0,
&gt;   "invalid_action_rate": 0.0,
&gt;   "policy_denial_rate": 0.0,
&gt;   "composite_score": 1.0,
&gt;   "total_actions": 9
&gt; &#125;</span></code></pre>
</div>

<div class="terminal margin-top">
  <div class="terminal-bar">
    <div class="dots" aria-hidden="true">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
    </div>
    <span class="title">Terminal — support-ticket</span>
  </div>

  <pre class="terminal-body"><code><span class="command">$ uv run autoharness compare -e support-ticket -c no-harness,manual -d test</span>

<span class="output">&gt; Loaded 9 scenarios from scenarios/support-ticket/test.jsonl
&gt;
&gt;                        Comparison: support-ticket (test)
&gt; ┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
&gt; ┃            ┃              ┃              ┃ Policy      ┃           ┃         ┃
&gt; ┃ Condition  ┃ Success Rate ┃ Invalid Rate ┃ Denial      ┃ Composite ┃ Actions ┃
&gt; ┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
&gt; │ no-harness │ 77.8%        │ 19.1%        │ 73.0%       │ 0.609     │ 89      │
&gt; │ manual     │ 77.8%        │ 19.1%        │ 73.0%       │ 0.609     │ 89      │
&gt; └────────────┴──────────────┴──────────────┴─────────────┴───────────┴─────────┘</span></code></pre>
</div>

<style>
  .terminal {
    background: var(--slate-900);
    border: 1px solid var(--slate-800);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 0 30px rgba(34, 211, 238, 0.1);
  }

  .margin-top {
    margin-top: 1.5rem;
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
