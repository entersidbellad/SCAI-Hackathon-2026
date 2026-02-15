'use client';

import { useMemo, useState, useEffect, useRef } from 'react';
import styles from './page.module.css';
import RunnerConnect from '../components/run/RunnerConnect';
import CaseInput from '../components/run/CaseInput';
import ModelPicker from '../components/run/ModelPicker';
import RunResults from '../components/run/RunResults';

const DEFAULT_RUNNER_URL = 'http://127.0.0.1:8787';
const MODEL_LIMIT = 3;
const RUN_MODE_STANDARD = 'standard';
const RUN_MODE_STUDY = 'study';
const CUSTOM_MODEL_ID_REGEX = /^[a-zA-Z0-9._:/-]{2,120}$/;
const EMPTY_API_KEYS = { openai: '', anthropic: '', gemini: '', openrouter: '' };

const MODEL_CATALOG = [
  {
    provider: 'openai',
    label: 'OpenAI',
    models: [
      { id: 'gpt-4o-mini', label: 'gpt-4o-mini' },
      { id: 'gpt-4.1-mini', label: 'gpt-4.1-mini' },
    ],
  },
  {
    provider: 'anthropic',
    label: 'Anthropic',
    models: [
      { id: 'claude-3-5-haiku-latest', label: 'claude-3-5-haiku-latest' },
      { id: 'claude-3-5-sonnet-latest', label: 'claude-3-5-sonnet-latest' },
    ],
  },
  {
    provider: 'gemini',
    label: 'Gemini',
    models: [
      { id: 'gemini-1.5-flash', label: 'gemini-1.5-flash' },
      { id: 'gemini-1.5-pro', label: 'gemini-1.5-pro' },
    ],
  },
];

const KEY_PROVIDERS = [
  { provider: 'openai', label: 'OpenAI' },
  { provider: 'anthropic', label: 'Anthropic' },
  { provider: 'gemini', label: 'Gemini' },
  { provider: 'openrouter', label: 'OpenRouter' },
];

const COST_PER_1K = {
  openai: { input: 0.002, output: 0.006 },
  anthropic: { input: 0.003, output: 0.015 },
  gemini: { input: 0.0015, output: 0.0045 },
  openrouter: { input: 0.004, output: 0.012 },
};

function createCustomModelRow(id) {
  return {
    id: `custom-${id}`,
    provider: 'openrouter',
    model: '',
    label: '',
  };
}

function estimateTokens(text) {
  return Math.ceil((text || '').length / 4);
}

function estimateRunBudget(caseText, referenceSummary, selectedModels) {
  const modelCount = Math.max(1, selectedModels.length);
  const inputTokens = estimateTokens(caseText) + estimateTokens(referenceSummary) + 280;
  const outputTokens = 760;
  const hasVariablePricing = selectedModels.some(
    (model) => model.source === 'custom' || model.provider === 'openrouter',
  );

  let maxUsd = 0;
  for (const model of selectedModels) {
    const providerCost = COST_PER_1K[model.provider] || COST_PER_1K.openai;
    maxUsd += (inputTokens / 1000) * providerCost.input;
    maxUsd += (outputTokens / 1000) * providerCost.output;
  }

  maxUsd *= 1.25;

  return {
    inputTokens: inputTokens * modelCount,
    outputTokens: outputTokens * modelCount,
    totalTokens: (inputTokens + outputTokens) * modelCount,
    maxUsd,
    hasVariablePricing,
  };
}

function toMarkdown(result) {
  const rows = result.models
    .map(
      (model) =>
        `| ${model.model} | ${model.score_mode} | ${formatScore(model.composite_score)} | ${formatScore(
          model.pillars.nli.value,
        )} | ${formatScore(model.pillars.judge.value)} | ${formatScore(model.pillars.coverage.value)} |`,
    )
    .join('\n');

  return [
    '# ∑VAL Local Run Report',
    '',
    `- Generated at: ${new Date().toISOString()}`,
    `- Score mode: ${result.score_mode}`,
    result.non_comparability_note ? `- Note: ${result.non_comparability_note}` : null,
    '',
    '| Model | Mode | Composite | NLI | Judge | Coverage |',
    '| --- | --- | ---: | ---: | ---: | ---: |',
    rows,
    '',
  ]
    .filter(Boolean)
    .join('\n');
}

function formatScore(value) {
  return value == null || !Number.isFinite(value) ? '—' : value.toFixed(3);
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || 'Request failed.');
  }
  return payload;
}

function authHeaders(connection) {
  return {
    'X-Session-Id': connection.sessionId,
    'X-Csrf-Token': connection.csrfToken,
  };
}

export default function RunYourCasePage() {
  const [runnerUrl, setRunnerUrl] = useState(DEFAULT_RUNNER_URL);
  const [connectionBusy, setConnectionBusy] = useState(false);
  const [connection, setConnection] = useState({
    status: 'disconnected',
    sessionId: '',
    csrfToken: '',
    health: null,
    error: '',
  });

  const [caseText, setCaseText] = useState('');
  const [referenceSummary, setReferenceSummary] = useState('');
  const [fileMeta, setFileMeta] = useState(null);
  const [uploadBusy, setUploadBusy] = useState(false);

  const [apiKeys, setApiKeys] = useState(EMPTY_API_KEYS);
  const [selectedPresetModels, setSelectedPresetModels] = useState([]);
  const [customModels, setCustomModels] = useState([createCustomModelRow(1)]);
  const customCounterRef = useRef(2);

  const modelSelection = useMemo(() => {
    const dedupe = new Map();

    for (const entry of selectedPresetModels) {
      dedupe.set(`${entry.provider}:${entry.model}`, entry);
    }

    for (const row of customModels) {
      const model = row.model.trim();
      if (!model) continue;
      if (!CUSTOM_MODEL_ID_REGEX.test(model)) continue;
      const label = row.label.trim() || model;
      const key = `${row.provider}:${model}`;
      if (!dedupe.has(key)) {
        dedupe.set(key, {
          provider: row.provider,
          model,
          label,
          source: 'custom',
        });
      }
    }

    const entries = [...dedupe.values()];
    return {
      entries,
      total: entries.length,
      overflow: Math.max(0, entries.length - MODEL_LIMIT),
    };
  }, [selectedPresetModels, customModels]);

  const selectedEntries = modelSelection.entries;
  const selectedModels = selectedEntries.slice(0, MODEL_LIMIT);
  const modelOverflow = modelSelection.overflow;

  const [runMode, setRunMode] = useState(RUN_MODE_STANDARD);
  const [costConfirmed, setCostConfirmed] = useState(false);
  const [ackPrivacyAndLimits, setAckPrivacyAndLimits] = useState(false);
  const [runBusy, setRunBusy] = useState(false);
  const [runError, setRunError] = useState('');
  const [runStatus, setRunStatus] = useState('');
  const [runId, setRunId] = useState('');
  const [runResult, setRunResult] = useState(null);

  const estimate = useMemo(
    () => estimateRunBudget(caseText, referenceSummary, selectedEntries),
    [caseText, referenceSummary, selectedEntries],
  );

  const isConnected = connection.status === 'connected';
  const studyMode = runMode === RUN_MODE_STUDY;
  const hasReferenceSummary = Boolean(referenceSummary.trim());
  const canStartRun =
    isConnected &&
    Boolean(caseText.trim()) &&
    selectedEntries.length > 0 &&
    modelOverflow === 0 &&
    costConfirmed &&
    ackPrivacyAndLimits &&
    (!studyMode || hasReferenceSummary) &&
    !runBusy &&
    !uploadBusy;

  useEffect(() => {
    const handleBeforeUnload = () => {
      setApiKeys(EMPTY_API_KEYS);
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  async function connectRunner() {
    setConnectionBusy(true);
    setRunError('');
    try {
      const base = runnerUrl.replace(/\/$/, '');
      const health = await parseResponse(await fetch(`${base}/health`, { method: 'GET' }));
      const session = await parseResponse(
        await fetch(`${base}/session/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        }),
      );

      setConnection({
        status: 'connected',
        sessionId: session.session_id,
        csrfToken: session.csrf_token,
        health,
        error: '',
      });
    } catch (error) {
      setConnection((prev) => ({
        ...prev,
        status: 'disconnected',
        error: error.message || 'Could not connect to local runner.',
      }));
    } finally {
      setConnectionBusy(false);
    }
  }

  async function clearSession() {
    if (!connection.sessionId) {
      setConnection({ status: 'disconnected', sessionId: '', csrfToken: '', health: null, error: '' });
      return;
    }

    setConnectionBusy(true);
    let cleared = false;

    try {
      const base = runnerUrl.replace(/\/$/, '');
      const response = await fetch(`${base}/session/${connection.sessionId}`, {
        method: 'DELETE',
        headers: {
          ...authHeaders(connection),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      cleared = response.ok;
    } catch {
      // no-op: local runner may already be offline
    } finally {
      setConnection({ status: 'disconnected', sessionId: '', csrfToken: '', health: null, error: '' });
      if (cleared) {
        setApiKeys(EMPTY_API_KEYS);
        setSelectedPresetModels([]);
        setCustomModels([createCustomModelRow(1)]);
        customCounterRef.current = 2;
        setCostConfirmed(false);
        setAckPrivacyAndLimits(false);
      }
      setConnectionBusy(false);
    }
  }

  async function handleParseFile(file) {
    if (!isConnected) {
      setRunError('Connect the local runner before uploading files.');
      return;
    }

    setUploadBusy(true);
    setRunError('');

    try {
      const base = runnerUrl.replace(/\/$/, '');
      const body = new FormData();
      body.append('file', file);

      const payload = await parseResponse(
        await fetch(`${base}/files/parse`, {
          method: 'POST',
          headers: authHeaders(connection),
          body,
        }),
      );

      setCaseText(payload.text || '');
      setFileMeta({ filename: payload.filename, charCount: payload.char_count || 0 });
    } catch (error) {
      setRunError(error.message || 'File parsing failed.');
    } finally {
      setUploadBusy(false);
    }
  }

  function handleTogglePresetModel(entry) {
    const key = `${entry.provider}:${entry.model}`;
    const exists = selectedPresetModels.some((item) => `${item.provider}:${item.model}` === key);

    if (!exists && modelSelection.total >= MODEL_LIMIT) {
      setRunError(`You can select up to ${MODEL_LIMIT} models per run.`);
      return;
    }

    setRunError('');
    setSelectedPresetModels((current) => {
      const present = current.some((item) => `${item.provider}:${item.model}` === key);
      if (present) {
        return current.filter((item) => `${item.provider}:${item.model}` !== key);
      }
      return [...current, { ...entry, source: 'preset' }];
    });
  }

  function handleCustomModelChange(rowId, field, value) {
    const nextValue = field === 'provider' ? value.toLowerCase() : value;
    setCustomModels((current) =>
      current.map((row) => (row.id === rowId ? { ...row, [field]: nextValue } : row)),
    );
  }

  function handleAddCustomModel() {
    setCustomModels((current) => {
      if (current.length >= 6) return current;
      const next = createCustomModelRow(customCounterRef.current);
      customCounterRef.current += 1;
      return [...current, next];
    });
  }

  function handleRemoveCustomModel(rowId) {
    setCustomModels((current) => {
      if (current.length <= 1) {
        return [createCustomModelRow(1)];
      }
      return current.filter((row) => row.id !== rowId);
    });
  }

  async function startRun() {
    setRunError('');

    if (!isConnected) {
      setRunError('Connect to the local runner first.');
      return;
    }
    if (!caseText.trim()) {
      setRunError('Case text is required.');
      return;
    }
    if (!selectedEntries.length) {
      setRunError('Select at least one model.');
      return;
    }
    if (modelOverflow > 0) {
      setRunError(`Select at most ${MODEL_LIMIT} models. You currently have ${modelSelection.total}.`);
      return;
    }
    if (customModels.some((row) => row.model.trim() && !CUSTOM_MODEL_ID_REGEX.test(row.model.trim()))) {
      setRunError('Fix invalid custom model IDs before running (allowed: letters, numbers, ., _, :, /, -).');
      return;
    }
    if (!costConfirmed) {
      setRunError('Please confirm cost bounds before running.');
      return;
    }
    if (!ackPrivacyAndLimits) {
      setRunError('Please acknowledge privacy, provider processing, and decision-support limitations.');
      return;
    }
    if (studyMode && !hasReferenceSummary) {
      setRunError('Study mode requires a reference summary so all runs use full 3-pillar scoring and remain comparable.');
      return;
    }

    setRunBusy(true);
    setRunStatus('queued');
    setRunResult(null);

    try {
      const base = runnerUrl.replace(/\/$/, '');
      const payload = await parseResponse(
        await fetch(`${base}/runs`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders(connection),
          },
          body: JSON.stringify({
            case_text: caseText,
            reference_summary: referenceSummary,
            selected_models: selectedModels,
            api_keys: apiKeys,
            run_mode: runMode,
            confirm_cost_ack: true,
          }),
        }),
      );

      if (payload.requires_confirmation) {
        setRunBusy(false);
        setRunError('Runner requires explicit cost confirmation. Please retry.');
        return;
      }

      setRunId(payload.run_id);
      setRunStatus(payload.status || 'queued');
    } catch (error) {
      setRunError(error.message || 'Run could not start.');
      setRunStatus('');
      setRunBusy(false);
    }
  }

  useEffect(() => {
    if (!runId) return undefined;
    if (!(runStatus === 'queued' || runStatus === 'running')) return undefined;

    let active = true;
    const base = runnerUrl.replace(/\/$/, '');

    const poll = async () => {
      try {
        const payload = await parseResponse(
          await fetch(`${base}/runs/${runId}`, {
            headers: {
              'X-Session-Id': connection.sessionId,
              'X-Csrf-Token': connection.csrfToken,
            },
          }),
        );

        if (!active) return;
        setRunStatus(payload.status || 'running');

        if (payload.status === 'completed') {
          setRunResult(payload.result || null);
          setRunBusy(false);
          return;
        }

        if (payload.status === 'failed') {
          setRunError(payload.error || 'Run failed.');
          setRunBusy(false);
        }
      } catch (error) {
        if (!active) return;
        setRunError(error.message || 'Failed to poll run status.');
        setRunBusy(false);
      }
    };

    const timer = setInterval(poll, 1800);
    poll();

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [runId, runStatus, runnerUrl, connection.sessionId, connection.csrfToken]);

  function handleDownloadJson() {
    if (!runResult) return;
    const blob = new Blob([JSON.stringify(runResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `eval-local-run-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function handleDownloadMarkdown() {
    if (!runResult) return;
    const blob = new Blob([toMarkdown(runResult)], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `eval-local-run-${Date.now()}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className={styles.pageWrap}>
      <div className="section-header">
        <h1 className="section-title">Run Your Case</h1>
        <p className="section-subtitle">
          Bring your own case, keys, and models. Execution runs locally so keys stay on your machine.
        </p>
      </div>

      <hr className="divider" />

      <p className={styles.lead}>
        This local simulation mirrors ∑VAL scoring logic. If you provide a trusted reference summary, you get full
        three-pillar scoring (NLI, Judge, Coverage). Without a reference, scores are marked provisional and are not
        directly comparable to leaderboard rankings.
      </p>

      <section className={styles.flowCard}>
        <h2 className={styles.flowTitle}>Quick Flow</h2>
        <ol className={styles.flowList}>
          <li>1. Start local runner.</li>
          <li>2. Connect from this page.</li>
          <li>3. Add case text or upload a file.</li>
          <li>4. Add provider keys and select 1-3 preset/custom models.</li>
          <li>5. Confirm cost estimate and run.</li>
        </ol>
      </section>

      <RunnerConnect
        runnerUrl={runnerUrl}
        onRunnerUrlChange={setRunnerUrl}
        connection={connection}
        onConnect={connectRunner}
        onDisconnect={clearSession}
        busy={connectionBusy}
      />

      <CaseInput
        caseText={caseText}
        referenceSummary={referenceSummary}
        onCaseTextChange={setCaseText}
        onReferenceSummaryChange={setReferenceSummary}
        onParseFile={handleParseFile}
        fileMeta={fileMeta}
        uploadBusy={uploadBusy}
        disabled={connectionBusy || runBusy}
      />

      <ModelPicker
        catalog={MODEL_CATALOG}
        keyProviders={KEY_PROVIDERS}
        selectedEntries={selectedEntries}
        selectedCount={modelSelection.total}
        overflowCount={modelOverflow}
        onTogglePresetModel={handleTogglePresetModel}
        customModels={customModels}
        onCustomModelChange={handleCustomModelChange}
        onAddCustomModel={handleAddCustomModel}
        onRemoveCustomModel={handleRemoveCustomModel}
        apiKeys={apiKeys}
        onApiKeyChange={(provider, value) => setApiKeys((current) => ({ ...current, [provider]: value }))}
        estimate={estimate}
        limit={MODEL_LIMIT}
        disabled={runBusy}
      />

      <section className={styles.runPanel}>
        <h2 className={styles.runTitle}>4) Confirm + Start</h2>
        <p className={styles.runMeta}>
          Conservative defaults: max 3 models, one case per run, token caps, and a 10-minute timeout.
        </p>

        <div className={styles.modeRow}>
          <span className={styles.modeLabel}>Run Mode</span>
          <div className={styles.modeButtons}>
            <button
              type="button"
              className={`${styles.modeButton} ${runMode === RUN_MODE_STANDARD ? styles.modeButtonActive : ''}`}
              onClick={() => setRunMode(RUN_MODE_STANDARD)}
              disabled={runBusy}
            >
              [standard]
            </button>
            <button
              type="button"
              className={`${styles.modeButton} ${runMode === RUN_MODE_STUDY ? styles.modeButtonActive : ''}`}
              onClick={() => setRunMode(RUN_MODE_STUDY)}
              disabled={runBusy}
            >
              [study]
            </button>
          </div>
        </div>

        <p className={styles.modeNote}>
          Study mode requires a reference summary so all runs use full 3-pillar scoring and remain comparable.
        </p>

        <div className={styles.controls}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={costConfirmed}
              onChange={(event) => setCostConfirmed(event.target.checked)}
              disabled={runBusy}
            />
            I confirm this run may use up to ~${estimate.maxUsd.toFixed(3)} in API costs.
          </label>

          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={ackPrivacyAndLimits}
              onChange={(event) => setAckPrivacyAndLimits(event.target.checked)}
              disabled={runBusy}
            />
            I understand keys are used locally for this session, provider APIs still receive submitted text, and
            results are decision-support signals (not legal advice or absolute truth).
          </label>

          <button type="button" className={styles.runButton} onClick={startRun} disabled={!canStartRun}>
            {runBusy ? '[running...]' : '[start run]'}
          </button>
        </div>

        {runError && <div className={styles.inlineError}>{runError}</div>}
      </section>

      <RunResults
        runStatus={runStatus}
        runError={runError}
        runResult={runResult}
        onDownloadJson={handleDownloadJson}
        onDownloadMarkdown={handleDownloadMarkdown}
      />
    </div>
  );
}
