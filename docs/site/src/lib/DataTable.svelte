<section class="table-shell" aria-label="Performance comparison">
  <header class="table-header">
    <p class="eyebrow">Evaluation Snapshot</p>
    <h3>Performance Comparison — Expense Approval (test set)</h3>
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
        <td>No Harness</td>
        <td>65.0%</td>
        <td>35.0%</td>
        <td>0.0%</td>
        <td>
          <div class="score-cell">
            <span>0.555</span>
            <span class="bar"><span style="width: 55.5%"></span></span>
          </div>
        </td>
      </tr>
      <tr>
        <td>Manual Harness</td>
        <td>85.0%</td>
        <td>10.0%</td>
        <td>5.0%</td>
        <td>
          <div class="score-cell">
            <span>0.802</span>
            <span class="bar"><span style="width: 80.2%"></span></span>
          </div>
        </td>
      </tr>
      <tr class="generated">
        <td>Generated Harness</td>
        <td class="highlight">88.0%</td>
        <td>5.0%</td>
        <td>7.0%</td>
        <td class="highlight">
          <div class="score-cell">
            <span>0.847</span>
            <span class="bar"><span style="width: 84.7%"></span></span>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
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
      linear-gradient(90deg, rgba(34, 211, 238, 0.18), rgba(34, 211, 238, 0.04) 18%, transparent 35%),
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

  @media (max-width: 780px) {
    .table-shell {
      overflow-x: auto;
    }

    table {
      min-width: 720px;
    }
  }
</style>
