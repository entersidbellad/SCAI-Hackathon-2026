'use client';

import styles from './run.module.css';

function fmtScore(value) {
  if (value == null || !Number.isFinite(value)) return '—';
  return value.toFixed(3);
}

function fmtPercent(value) {
  if (value == null || !Number.isFinite(value)) return '—';
  return `${Math.round(value * 100)}%`;
}

export default function RunResults({ runStatus, runError, runResult, onDownloadJson, onDownloadMarkdown }) {
  return (
    <section className={styles.panel}>
      <h2 className={styles.panelTitle}>5) Results</h2>
      <p className={styles.panelSub}>
        Scores are confidence signals. Higher is generally better, but not a guarantee of perfect truth.
      </p>

      {runStatus && <div className={styles.statusLine}>Run status: {runStatus}</div>}
      {runError && <div className={styles.error}>{runError}</div>}

      {!runResult && !runError && (
        <div className={styles.hint}>
          Start a run after selecting models. You will see a scorecard, per-pillar rationale, and optional downloads.
        </div>
      )}

      {runResult && (
        <>
          {Array.isArray(runResult.warnings) && runResult.warnings.length > 0 && (
            <div className={styles.warningBox}>
              {runResult.warnings.map((warning) => (
                <div key={warning}>{warning}</div>
              ))}
            </div>
          )}

          <div className={styles.tableWrap}>
            <table className={styles.resultTable}>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Mode</th>
                  <th>Composite</th>
                  <th>NLI</th>
                  <th>Judge</th>
                  <th>Coverage</th>
                  <th>Confidence</th>
                  <th>Summary</th>
                </tr>
              </thead>
              <tbody>
                {runResult.models.map((model) => (
                  <tr key={`${model.provider}:${model.model}`}>
                    <td>{model.model}</td>
                    <td>{model.score_mode}</td>
                    <td>{fmtScore(model.composite_score)}</td>
                    <td>{fmtScore(model.pillars.nli.value)}</td>
                    <td>{fmtScore(model.pillars.judge.value)}</td>
                    <td>{fmtScore(model.pillars.coverage.value)}</td>
                    <td>{fmtPercent(model.composite_confidence)}</td>
                    <td className={styles.summaryCell}>{model.summary_text || model.error || 'No output.'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className={styles.warningBox}>
            <div>Scoring mode: {runResult.score_mode}</div>
            {runResult.non_comparability_note && <div>{runResult.non_comparability_note}</div>}
          </div>

          <div className={styles.actions}>
            <button type="button" className={styles.button} onClick={onDownloadJson}>
              [download json]
            </button>
            <button type="button" className={styles.button} onClick={onDownloadMarkdown}>
              [download markdown]
            </button>
          </div>
        </>
      )}
    </section>
  );
}
