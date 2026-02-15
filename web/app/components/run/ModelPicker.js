'use client';

import styles from './run.module.css';

function modelKey(provider, model) {
  return `${provider}:${model}`;
}

export default function ModelPicker({
  catalog,
  keyProviders,
  selectedModels,
  onTogglePresetModel,
  customModels,
  onCustomModelChange,
  onToggleCustomModel,
  onAddCustomModel,
  onRemoveCustomModel,
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
              const checked = selectedKeys.has(key);
              return (
                <label className={styles.modelOption} key={key}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      onTogglePresetModel({ provider: group.provider, model: model.id, label: model.label, source: 'preset' })
                    }
                    disabled={disabled || (!checked && selectedModels.length >= limit)}
                  />
                  <span>{model.label}</span>
                </label>
              );
            })}
          </div>
        ))}
      </div>

      <div className={styles.customSection}>
        <div className={styles.customHeader}>
          <div className={styles.customTitle}>Custom Models (Any Slug)</div>
          <button
            type="button"
            className={styles.button}
            onClick={onAddCustomModel}
            disabled={disabled || customModels.length >= 6}
          >
            [add custom model]
          </button>
        </div>
        {customModels.map((row) => (
          <div className={styles.customRow} key={row.id}>
            <label className={styles.customToggle}>
              <input
                type="checkbox"
                checked={row.selected}
                onChange={() => onToggleCustomModel(row.id)}
                disabled={disabled || (!row.selected && selectedModels.length >= limit)}
              />
              <span>Use</span>
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Provider</span>
              <select
                className={styles.select}
                value={row.provider}
                onChange={(event) => onCustomModelChange(row.id, 'provider', event.target.value)}
                disabled={disabled}
              >
                {keyProviders.map((provider) => (
                  <option value={provider.provider} key={provider.provider}>
                    {provider.label}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Model ID</span>
              <input
                className={styles.input}
                type="text"
                value={row.model}
                onChange={(event) => onCustomModelChange(row.id, 'model', event.target.value)}
                placeholder="e.g. openai/gpt-4o-mini or anthropic/claude-3.5-sonnet"
                autoComplete="off"
                spellCheck={false}
                disabled={disabled}
              />
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Label (Optional)</span>
              <input
                className={styles.input}
                type="text"
                value={row.label}
                onChange={(event) => onCustomModelChange(row.id, 'label', event.target.value)}
                placeholder="Friendly name"
                autoComplete="off"
                spellCheck={false}
                disabled={disabled}
              />
            </label>

            <button
              type="button"
              className={styles.button}
              onClick={() => onRemoveCustomModel(row.id)}
              disabled={disabled || customModels.length <= 1}
            >
              [remove]
            </button>
          </div>
        ))}
      </div>

      <div className={styles.keyGrid}>
        {keyProviders.map((provider) => (
          <label className={styles.field} key={`${provider.provider}-key`}>
            <span className={styles.label}>{provider.label} API Key</span>
            <input
              className={styles.input}
              type="password"
              value={apiKeys[provider.provider] || ''}
              onChange={(event) => onApiKeyChange(provider.provider, event.target.value)}
              placeholder={`Paste ${provider.label} key`}
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
      {estimate.hasVariablePricing && (
        <div className={styles.hint}>
          Custom/OpenRouter model pricing varies by route. This is a conservative upper-bound estimate.
        </div>
      )}

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
