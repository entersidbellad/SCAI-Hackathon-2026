'use client';

import styles from './run.module.css';

export default function CaseInput({
  caseText,
  referenceSummary,
  onCaseTextChange,
  onReferenceSummaryChange,
  onParseFile,
  fileMeta,
  uploadBusy,
  disabled,
}) {
  return (
    <section className={styles.panel}>
      <h2 className={styles.panelTitle}>2) Add Your Case</h2>
      <p className={styles.panelSub}>
        Use paste or upload (.txt, .md, .pdf). Optional reference summary enables full 3-pillar scoring.
      </p>

      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>Case Text</span>
          <textarea
            className={styles.textarea}
            value={caseText}
            onChange={(event) => onCaseTextChange(event.target.value)}
            placeholder="Paste your case content here..."
            disabled={disabled}
          />
        </label>
      </div>

      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>Optional Reference Summary (Gold)</span>
          <textarea
            className={styles.textarea}
            value={referenceSummary}
            onChange={(event) => onReferenceSummaryChange(event.target.value)}
            placeholder="Optional: paste a trusted reference summary for full scoring"
            disabled={disabled}
          />
        </label>
      </div>

      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>Upload File</span>
          <input
            className={styles.input}
            type="file"
            accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onParseFile(file);
              event.target.value = '';
            }}
            disabled={disabled || uploadBusy}
          />
        </label>
      </div>

      {fileMeta && (
        <div className={styles.fileMeta}>
          Loaded file: {fileMeta.filename} ({fileMeta.charCount.toLocaleString()} chars)
        </div>
      )}

      {uploadBusy && <div className={styles.statusLine}>Parsing file...</div>}
    </section>
  );
}
