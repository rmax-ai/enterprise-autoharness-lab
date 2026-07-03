<div class="terminal">
  <div class="terminal-bar">
    <div class="dots" aria-hidden="true">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
    </div>
    <span class="title">Terminal — autoharness</span>
  </div>

  <pre class="terminal-body"><code><span class="command">$ pip install autoharness</span>
<span class="command">$ autoharness synthesize --env expense_approval</span>

<span class="output">&gt; Running noisy agent...                    [Done]
&gt; 14 failures collected.
&gt; Synthesizing harness (Iteration 1)...
&gt; AST Validation...                          [Passed]
&gt; Sandbox Testing...                         [Passed]
&gt; Evaluating... Score: 0.847 (Improved)
&gt; Harness promoted.                          [Active]</span>

<span class="command">$ autoharness compare --conditions no-harness,manual,generated</span>

<span class="output"> Condition            Success   Invalid   Composite
 ─────────────────────────────────────────────────
 no-harness           65.0%     35.0%     0.555
 manual               85.0%     10.0%     0.802
 generated            88.0%      5.0%     0.847</span></code></pre>
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
