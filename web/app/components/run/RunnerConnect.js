'use client';

import styles from './run.module.css';

export default function RunnerConnect({
  runnerUrl,
  onRunnerUrlChange,
  connection,
  onConnect,
  onDisconnect,
  busy,
}) {
  const isConnected = connection.status === 'connected';
  const dotClass = isConnected
    ? `${styles.dot} ${styles.dotConnected}`
    : busy
      ? `${styles.dot} ${styles.dotBusy}`
      : styles.dot;

  return (
    <section className={styles.panel}>
      <h2 className={styles.panelTitle}>1) Connect Local Runner</h2>
      <p className={styles.panelSub}>
        Run execution happens on your laptop. API keys stay in local runner memory only.
      </p>

      <div className={styles.command}>
        npm --prefix local-runner install && npm --prefix local-runner start
      </div>

      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>Runner URL</span>
          <input
            className={styles.input}
            value={runnerUrl}
            onChange={(event) => onRunnerUrlChange(event.target.value)}
            placeholder="http://127.0.0.1:8787"
            spellCheck={false}
          />
        </label>
      </div>

      <div className={styles.row}>
        <button type="button" className={`${styles.button} ${styles.buttonPrimary}`} onClick={onConnect} disabled={busy}>
          {busy ? '[connecting...]' : '[connect]'}
        </button>
        <button type="button" className={styles.button} onClick={onDisconnect} disabled={busy || !isConnected}>
          [clear session]
        </button>
      </div>

      <div className={styles.statusLine}>
        <span className={dotClass} aria-hidden="true" />
        <span>
          {isConnected
            ? `Connected | session ${connection.sessionId?.slice(0, 8)}... | version ${connection.health?.version || 'unknown'}`
            : 'Not connected'}
        </span>
      </div>

      {connection.error && <div className={styles.error}>{connection.error}</div>}
    </section>
  );
}
