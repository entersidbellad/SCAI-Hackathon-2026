'use client';

import styles from './run.module.css';

function modelKey(provider, model) {
  return `${provider}:${model}`;
}

export default function ModelPicker({
  catalog,
  selectedModels,
  onToggleModel,
  apiKeys,
  onApiKeyChange,
  estimate,
  limit,
  disabled,
}) {
  const selectedKeys = new Set(selectedModels.map((entry) => modelKey(entry.provider, entry.model)));

  return (
    <section className={styles.panel}>
      <h2 className={styles.panelTitle}>3) Choose Models + Keys</h2>
      <p className={styles.panelSub}>
        Select up to {limit} models. Keys are used only for this local runner session.
      </p>

      <div className={styles.modelGrid}>
        {catalog.map((group) => (
          <div key={group.provider} className={styles.modelCard}>
            <div className={styles.modelProvider}>{group.label}</div>
            {group.models.map((model) => {
              const key = modelKey(group.provider, model.id);
              return (
                <label className={styles.modelOption} key={key}>
                  <input
                    type="checkbox"
                    checked={selectedKeys.has(key)}
                    onChange={() => onToggleModel({ provider: group.provider, model: model.id, label: model.label })}
                    disabled={disabled}
                  />
                  <span>{model.label}</span>
                </label>
              );
            })}
          </div>
        ))}
      </div>

      <div className={styles.keyGrid}>
        {catalog.map((group) => (
          <label className={styles.field} key={`${group.provider}-key`}>
            <span className={styles.label}>{group.label} API Key</span>
            <input
              className={styles.input}
              type="password"
              value={apiKeys[group.provider] || ''}
              onChange={(event) => onApiKeyChange(group.provider, event.target.value)}
              placeholder={`Paste ${group.label} key`}
              autoComplete="off"
              spellCheck={false}
              disabled={disabled}
            />
          </label>
        ))}
      </div>

      <div className={styles.disclaimerBox}>
        Your API keys are sent only to your local runner (`127.0.0.1`) and kept in memory for this session.
        They are not stored by ∑VAL cloud services. Do not use sensitive personal data unless you are authorized
        to share it with the model provider.
      </div>

      <div className={styles.hint}>
        Selected models: {selectedModels.length}/{limit}. Estimated upper bound before confirm:
        {' '}
        ~{estimate.totalTokens.toLocaleString()} tokens, ${estimate.maxUsd.toFixed(3)}.
      </div>

      <div className={styles.kvGrid}>
        <div className={styles.kvCard}>
          <div className={styles.kvLabel}>Input Tokens</div>
          <div className={styles.kvValue}>{estimate.inputTokens.toLocaleString()}</div>
        </div>
        <div className={styles.kvCard}>
          <div className={styles.kvLabel}>Output Tokens</div>
          <div className={styles.kvValue}>{estimate.outputTokens.toLocaleString()}</div>
        </div>
        <div className={styles.kvCard}>
          <div className={styles.kvLabel}>Total Upper Bound</div>
          <div className={styles.kvValue}>${estimate.maxUsd.toFixed(3)}</div>
        </div>
      </div>
    </section>
  );
}
