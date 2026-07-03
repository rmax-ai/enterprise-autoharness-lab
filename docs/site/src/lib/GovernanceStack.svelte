<div class="stack">
  <div class="feedback-dot" aria-hidden="true"></div>

  <div class="layer agent-layer">
    <span class="label">Generation Layer</span>
    <div class="agent-shape">
      <strong>The Agent</strong>
      <p>LLM Agent proposes action</p>
    </div>
  </div>

  <div class="connector"></div>

  <div class="layer harness-layer">
    <span class="label">Execution Boundary</span>
    <div class="code-card">
      <pre><code><span class="line"><span class="kw">def</span> <span class="fn">evaluate</span>(action, state):</span>
<span class="line">    <span class="kw">return</span> &#123;</span>
<span class="line">        <span class="key">"rejected"</span>: violates_harness_rules(action, state),</span>
<span class="line">        <span class="key">"reason"</span>: <span class="key">"generated harness evaluates action"</span>,</span>
<span class="line">    &#125;</span></code></pre>
    </div>
  </div>

  <div class="connector"></div>

  <div class="layer policy-layer">
    <span class="label">Authority Layer</span>
    <div class="policy-card">
      <span class="lock" aria-hidden="true">🔒</span>
      <div>
        <strong>Policy Engine</strong>
        <p>Final Authority</p>
      </div>
    </div>
  </div>
</div>

<style>
  .stack {
    position: relative;
    max-width: 760px;
    min-height: 400px;
    margin: 0 auto;
    display: grid;
    grid-template-rows: auto 24px auto 24px auto;
    gap: 0.5rem;
    align-items: center;
    padding-bottom: 1rem;
  }

  .layer {
    display: grid;
    justify-items: center;
    gap: 1rem;
  }

  .label {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--slate-400);
  }

  .agent-shape {
    width: min(100%, 420px);
    min-height: 110px;
    padding: 1.75rem 2rem;
    border: 1.5px dashed rgba(34, 211, 238, 0.45);
    border-radius: 999px;
    background:
      radial-gradient(circle at 30% 20%, rgba(34, 211, 238, 0.12), transparent 45%),
      rgba(15, 23, 42, 0.65);
    text-align: center;
    box-shadow: inset 0 0 40px rgba(34, 211, 238, 0.06);
  }

  .agent-shape strong,
  .policy-card strong {
    display: block;
    font-family: var(--font-mono);
    font-size: 1.2rem;
    color: var(--slate-50);
    margin-bottom: 0.35rem;
  }

  .agent-shape p,
  .policy-card p {
    color: var(--slate-400);
  }

  .connector {
    width: 2px;
    height: 100%;
    margin: 0 auto;
    background: linear-gradient(to bottom, rgba(34, 211, 238, 0.05), rgba(34, 211, 238, 0.45));
  }

  .code-card {
    width: min(100%, 520px);
    padding: 1.5rem;
    border: 1px solid rgba(34, 211, 238, 0.7);
    border-radius: 14px;
    background:
      linear-gradient(180deg, rgba(34, 211, 238, 0.08), rgba(2, 6, 23, 0.94)),
      var(--slate-900);
    box-shadow:
      0 0 30px rgba(34, 211, 238, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }

  pre {
    margin: 0;
    overflow-x: auto;
    font-family: var(--font-mono);
    font-size: 0.95rem;
    line-height: 1.7;
    color: var(--slate-200);
  }

  .line {
    display: block;
  }

  .kw {
    color: #7dd3fc;
  }

  .fn {
    color: #f8fafc;
  }

  .key {
    color: #67e8f9;
  }

  .policy-card {
    width: min(100%, 540px);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 1.4rem 1.75rem;
    border: 1px solid var(--slate-800);
    border-radius: 14px;
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
  }

  .lock {
    font-size: 1.8rem;
  }

  .feedback-dot {
    position: absolute;
    left: 50%;
    top: 40px;
    width: 8px;
    height: 8px;
    margin-left: -4px;
    border-radius: 50%;
    background: var(--cyan-400);
    box-shadow: 0 0 16px rgba(34, 211, 238, 0.9);
    animation: feedback-loop 3.2s ease-in-out infinite;
  }

  @keyframes feedback-loop {
    0%,
    100% {
      transform: translateY(0);
      opacity: 0.8;
    }

    40% {
      transform: translateY(128px);
      opacity: 1;
    }

    52% {
      transform: translateY(136px);
    }

    60% {
      transform: translateY(122px);
    }
  }

  @media (max-width: 640px) {
    .stack {
      height: auto;
      grid-template-rows: auto 20px auto 20px auto;
      padding-block: 1rem;
    }

    .agent-shape {
      border-radius: 32px;
    }
  }
</style>
