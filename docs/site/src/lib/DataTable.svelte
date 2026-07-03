<section class="table-shell" aria-label="Performance comparison">
  <header class="table-header">
    <p class="eyebrow">Benchmark Results</p>
    <h3>Performance Comparison — Expense Approval (test set, 4 scenarios)</h3>
    <p class="results-link">
      Raw data: <a href="https://github.com/rmax-ai/enterprise-autoharness-lab/tree/main/docs/benchmarks" target="_blank" rel="noopener">docs/benchmarks/</a>
    </p>
  </header>

  <table>
    <thead>
      <tr>
        <th>Condition</th>
        <th>Success Rate</th>
        <th>Invalid Rate</th>
        <th>Policy Denial</th>
        <th>Composite Score</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><span class="condition-label">Noisy Agent</span> <span class="sub">no harness</span></td>
        <td class="bad">0.0%</td>
        <td class="bad">100.0%</td>
        <td>0.0%</td>
        <td>
          <div class="score-cell">
            <span>−0.50</span>
            <span class="bar"><span style="width: 0%"></span></span>
          </div>
        </td>
      </tr>
      <tr>
        <td><span class="condition-label">Noisy Agent</span> <span class="sub">+ manual harness</span></td>
        <td class="bad">0.0%</td>
        <td class="bad">100.0%</td>
        <td>0.0%</td>
        <td>
          <div class="score-cell">
            <span>−0.50</span>
            <span class="bar"><span style="width: 0%"></span></span>
          </div>
        </td>
      </tr>
      <tr class="generated">
        <td><span class="condition-label">Scripted Agent</span> <span class="sub">deterministic baseline</span></td>
        <td class="highlight">100.0%</td>
        <td class="highlight">0.0%</td>
        <td class="highlight">0.0%</td>
        <td class="highlight">
          <div class="score-cell">
            <span>1.00</span>
            <span class="bar"><span style="width: 100%"></span></span>
          </div>
        </td>
      </tr>
    </tbody>
  </table>

  <footer class="table-footer">
    The noisy agent demonstrates the baseline chaos (100% invalid actions) that
    motivates this project. The scripted agent represents a deterministic
    oracle. AutoHarness bridges these two: synthesizing code that filters
    invalid actions before they reach the environment.
  </footer>
</section>

<style>
  .table-shell {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 23, 0.96));
    border: 1px solid var(--slate-800);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 0 30px rgba(34, 211, 238, 0.1);
  }

  .table-header {
    padding: 1.5rem 1.5rem 1rem;
    border-bottom: 1px solid var(--slate-800);
  }

  .eyebrow {
    margin-bottom: 0.35rem;
    color: var(--slate-400);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  h3 {
    font-family: var(--font-mono);
    font-size: 1.15rem;
    color: var(--slate-50);
    margin: 0 0 0.25rem;
  }

  .results-link {
    margin: 0;
    font-size: 0.8rem;
    color: var(--slate-400);
  }

  .results-link a {
    color: var(--cyan-400);
    text-decoration: none;
    font-family: var(--font-mono);
  }

  .results-link a:hover {
    text-decoration: underline;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 1rem 1.5rem;
    text-align: left;
    border-bottom: 1px solid var(--slate-800);
    font-size: 0.95rem;
  }

  th {
    color: var(--slate-400);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    background: rgba(15, 23, 42, 0.65);
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  tbody tr:hover {
    background: rgba(30, 41, 59, 0.45);
  }

  .generated {
    position: relative;
    background:
      linear-gradient(90deg, rgba(34, 211, 238, 0.14), rgba(34, 211, 238, 0.03) 18%, transparent 35%),
      rgba(15, 23, 42, 0.5);
  }

  .generated td:first-child {
    border-left: 3px solid var(--cyan-400);
    box-shadow: inset 8px 0 24px rgba(34, 211, 238, 0.06);
  }

  .highlight {
    color: var(--cyan-400);
    font-weight: 600;
  }

  .bad {
    color: #f87171;
    font-weight: 600;
  }

  .condition-label {
    display: block;
    font-weight: 600;
    color: var(--slate-200);
  }

  .sub {
    display: block;
    font-size: 0.78rem;
    color: var(--slate-400);
    font-family: var(--font-mono);
  }

  .score-cell {
    display: grid;
    grid-template-columns: auto minmax(100px, 1fr);
    gap: 0.75rem;
    align-items: center;
  }

  .bar {
    display: block;
    width: 100%;
    height: 8px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.16);
    overflow: hidden;
  }

  .bar span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, rgba(34, 211, 238, 0.65), var(--cyan-400));
  }

  .table-footer {
    padding: 1rem 1.5rem;
    font-size: 0.85rem;
    color: var(--slate-400);
    border-top: 1px solid var(--slate-800);
    line-height: 1.6;
  }

  @media (max-width: 780px) {
    .table-shell {
      overflow-x: auto;
    }

    table {
      min-width: 720px;
    }
  }
</style>
