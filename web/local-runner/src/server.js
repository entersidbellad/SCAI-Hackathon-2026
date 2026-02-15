const crypto = require('crypto');
const path = require('path');

const cors = require('cors');
const express = require('express');
const multer = require('multer');
const pdfParse = require('pdf-parse');

const { runOpenAI } = require('./providers/openai');
const { runAnthropic } = require('./providers/anthropic');
const { runGemini } = require('./providers/gemini');
const { evaluatePillars } = require('./scoring/pillars');
const { buildComposite } = require('./scoring/composite');

const VERSION = '0.1.0';
const HOST = '127.0.0.1';
const PORT = Number(process.env.RUNNER_PORT || 8787);

const SESSION_TTL_MS = 30 * 60 * 1000;
const RUN_TIMEOUT_MS = 10 * 60 * 1000;
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_CASE_CHARS = 60000;
const MAX_REFERENCE_CHARS = 18000;
const MAX_MODELS = 3;
const MAX_INPUT_TOKENS = 42000;
const RUN_MODE_STANDARD = 'standard';
const RUN_MODE_STUDY = 'study';

const PROVIDERS = {
  openai: runOpenAI,
  anthropic: runAnthropic,
  gemini: runGemini,
};

const PRICE_PER_1K = {
  openai: { input: 0.002, output: 0.006 },
  anthropic: { input: 0.003, output: 0.015 },
  gemini: { input: 0.0015, output: 0.0045 },
};

const sessions = new Map();
const runs = new Map();

const defaultOrigins = [
  'http://localhost:3000',
  'http://127.0.0.1:3000',
];

const configuredOrigins = String(process.env.RUNNER_ALLOWED_ORIGINS || '')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean);

const allowedOrigins = new Set([...defaultOrigins, ...configuredOrigins]);

const app = express();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: MAX_FILE_BYTES },
});

app.use(
  cors({
    origin(origin, callback) {
      if (!origin) return callback(null, true);
      if (allowedOrigins.has(origin)) return callback(null, true);
      return callback(new Error('Origin not allowed by local runner CORS policy.'));
    },
    methods: ['GET', 'POST', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'X-Session-Id', 'X-Csrf-Token'],
    maxAge: 600,
  }),
);
app.use(express.json({ limit: '1mb' }));

app.use((req, res, next) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  next();
});

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    version: VERSION,
    host: HOST,
    port: PORT,
    providers: Object.keys(PROVIDERS),
    allowed_origins: [...allowedOrigins],
    constraints: {
      max_models: MAX_MODELS,
      max_case_chars: MAX_CASE_CHARS,
      max_reference_chars: MAX_REFERENCE_CHARS,
      max_file_bytes: MAX_FILE_BYTES,
      run_timeout_ms: RUN_TIMEOUT_MS,
    },
  });
});

app.post('/session/start', (req, res) => {
  const session_id = randomId(16);
  const csrf_token = randomId(16);
  const now = Date.now();

  sessions.set(session_id, {
    session_id,
    csrf_token,
    created_at: now,
    touched_at: now,
    keys: {},
  });

  res.status(201).json({
    session_id,
    csrf_token,
    expires_in_seconds: SESSION_TTL_MS / 1000,
  });
});

app.post('/files/parse', upload.single('file'), async (req, res) => {
  try {
    const session = requireSession(req, res);
    if (!session) return;

    const file = req.file;
    if (!file) {
      return res.status(400).json({ error: 'No file provided.' });
    }

    const ext = path.extname(String(file.originalname || '')).toLowerCase();
    if (!['.txt', '.md', '.pdf'].includes(ext)) {
      return res.status(400).json({ error: 'Unsupported file type. Use .txt, .md, or .pdf.' });
    }

    let text = '';
    if (ext === '.pdf') {
      const parsed = await pdfParse(file.buffer);
      text = String(parsed.text || '');
    } else {
      text = file.buffer.toString('utf8');
    }

    const normalized = normalizeText(text, MAX_CASE_CHARS);
    if (!normalized.trim()) {
      return res.status(400).json({ error: 'File parsed, but no usable text was found.' });
    }

    return res.json({
      filename: file.originalname,
      mime_type: file.mimetype || 'application/octet-stream',
      char_count: normalized.length,
      text: normalized,
    });
  } catch {
    return res.status(500).json({ error: 'Failed to parse uploaded file.' });
  }
});

app.post('/runs', async (req, res) => {
  try {
    const session = requireSession(req, res);
    if (!session) return;

    const caseText = normalizeText(req.body?.case_text, MAX_CASE_CHARS);
    const referenceSummary = normalizeText(req.body?.reference_summary, MAX_REFERENCE_CHARS);
    const selectedModels = normalizeModels(req.body?.selected_models);
    const apiKeys = normalizeKeys(req.body?.api_keys || {});
    const runMode = normalizeRunMode(req.body?.run_mode);
    const confirmCost = Boolean(req.body?.confirm_cost_ack);

    if (!caseText) {
      return res.status(400).json({ error: 'case_text is required.' });
    }

    if (!selectedModels.length) {
      return res.status(400).json({ error: 'At least one model must be selected.' });
    }

    if (selectedModels.length > MAX_MODELS) {
      return res.status(400).json({ error: `Maximum ${MAX_MODELS} models allowed per run.` });
    }

    if (runMode === RUN_MODE_STUDY && !referenceSummary) {
      return res.status(400).json({
        error: 'Study mode requires a reference summary so all runs use full 3-pillar scoring and remain comparable.',
      });
    }

    const estimatedInputTokens = estimateTokens(caseText) + estimateTokens(referenceSummary) + 280;
    if (estimatedInputTokens > MAX_INPUT_TOKENS) {
      return res.status(400).json({ error: 'Case text is too large for conservative token limits.' });
    }

    session.keys = {
      ...session.keys,
      ...apiKeys,
    };

    const missingProviders = selectedModels
      .map((model) => model.provider)
      .filter((provider, idx, arr) => arr.indexOf(provider) === idx)
      .filter((provider) => !session.keys[provider]);

    if (missingProviders.length) {
      return res.status(400).json({
        error: `Missing API key for: ${missingProviders.join(', ')}. Keys are session-only and not persisted.`,
      });
    }

    const estimate = estimateRun(selectedModels, caseText, referenceSummary);

    if (!confirmCost) {
      return res.status(200).json({
        requires_confirmation: true,
        estimate,
        limits: {
          max_models: MAX_MODELS,
          max_runtime_seconds: RUN_TIMEOUT_MS / 1000,
          max_input_tokens: MAX_INPUT_TOKENS,
        },
      });
    }

    const run_id = randomId(14);
    const scoreMode = runMode === RUN_MODE_STUDY || referenceSummary ? 'full' : 'provisional';

    const runRecord = {
      run_id,
      session_id: session.session_id,
      status: 'queued',
      created_at: Date.now(),
      accepted_config: {
        selected_models: selectedModels,
        run_mode: runMode,
        score_mode: scoreMode,
      },
      estimate,
      result: null,
      error: null,
    };

    runs.set(run_id, runRecord);

    executeRun({
      run_id,
      caseText,
      referenceSummary,
      selectedModels,
      keys: session.keys,
      runMode,
    }).catch((error) => {
      const current = runs.get(run_id);
      if (!current) return;
      current.status = 'failed';
      current.error = error.message || 'Run failed.';
      current.completed_at = Date.now();
    });

    return res.status(202).json({
      run_id,
      status: 'queued',
      accepted_config: runRecord.accepted_config,
      estimate,
    });
  } catch {
    return res.status(500).json({ error: 'Could not start run.' });
  }
});

app.get('/runs/:run_id', (req, res) => {
  const session = requireSession(req, res);
  if (!session) return;

  const run = runs.get(String(req.params.run_id || ''));
  if (!run || run.session_id !== session.session_id) {
    return res.status(404).json({ error: 'Run not found.' });
  }

  return res.json({
    run_id: run.run_id,
    status: run.status,
    accepted_config: run.accepted_config,
    estimate: run.estimate,
    result: run.result,
    error: run.error,
    created_at: run.created_at,
    completed_at: run.completed_at || null,
  });
});

app.delete('/session/:session_id', (req, res) => {
  const session_id = String(req.params.session_id || '').trim();
  const csrf_token = String(req.body?.csrf_token || req.headers['x-csrf-token'] || '').trim();
  const headerSession = String(req.headers['x-session-id'] || '').trim();

  if (headerSession && headerSession !== session_id) {
    return res.status(401).json({ error: 'Session ID mismatch.' });
  }

  const session = sessions.get(session_id);
  if (!session || session.csrf_token !== csrf_token) {
    return res.status(401).json({ error: 'Invalid session or CSRF token.' });
  }

  sessions.delete(session_id);

  for (const [run_id, run] of runs.entries()) {
    if (run.session_id === session_id) {
      runs.delete(run_id);
    }
  }

  return res.json({ ok: true });
});

app.use((error, req, res, next) => {
  if (error && error.message && error.message.includes('CORS')) {
    return res.status(403).json({ error: error.message });
  }

  if (error?.code === 'LIMIT_FILE_SIZE') {
    return res.status(400).json({ error: 'File exceeds 10MB limit.' });
  }

  return res.status(500).json({ error: 'Unhandled local runner error.' });
});

app.listen(PORT, HOST, () => {
  console.log(`∑VAL local runner listening on http://${HOST}:${PORT}`);
});

setInterval(() => {
  const now = Date.now();
  for (const [session_id, session] of sessions.entries()) {
    if (now - session.touched_at > SESSION_TTL_MS) {
      sessions.delete(session_id);
      for (const [run_id, run] of runs.entries()) {
        if (run.session_id === session_id) runs.delete(run_id);
      }
    }
  }
}, 60_000).unref();

function requireSession(req, res) {
  const session_id = String(
    req.body?.session_id || req.headers['x-session-id'] || '',
  ).trim();
  const csrf_token = String(
    req.body?.csrf_token || req.headers['x-csrf-token'] || '',
  ).trim();

  if (!/^[a-f0-9]{16,64}$/i.test(session_id) || !/^[a-f0-9]{16,64}$/i.test(csrf_token)) {
    res.status(401).json({ error: 'Missing or invalid session credentials.' });
    return null;
  }

  const session = sessions.get(session_id);
  if (!session || session.csrf_token !== csrf_token) {
    res.status(401).json({ error: 'Session authentication failed.' });
    return null;
  }

  session.touched_at = Date.now();
  return session;
}

function normalizeText(value, limit) {
  return String(value || '')
    .replace(/[\u0000-\u001F\u007F]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, limit);
}

function normalizeModels(input) {
  if (!Array.isArray(input)) return [];

  const dedupe = new Map();
  for (const raw of input) {
    const provider = String(raw?.provider || '').toLowerCase().trim();
    const model = String(raw?.model || '').trim();

    if (!Object.prototype.hasOwnProperty.call(PROVIDERS, provider)) continue;
    if (!/^[a-zA-Z0-9._:\/-]{2,120}$/.test(model)) continue;

    const key = `${provider}:${model}`;
    if (!dedupe.has(key)) {
      dedupe.set(key, {
        provider,
        model,
        label: String(raw?.label || model).slice(0, 120),
      });
    }
  }

  return [...dedupe.values()].slice(0, MAX_MODELS);
}

function normalizeKeys(input) {
  const normalized = {};
  for (const provider of Object.keys(PROVIDERS)) {
    const key = String(input?.[provider] || '').trim();
    if (key) normalized[provider] = key.slice(0, 300);
  }
  return normalized;
}

function normalizeRunMode(input) {
  const mode = String(input || RUN_MODE_STANDARD).toLowerCase().trim();
  if (mode === RUN_MODE_STUDY) return RUN_MODE_STUDY;
  return RUN_MODE_STANDARD;
}

function estimateTokens(text) {
  return Math.ceil(String(text || '').length / 4);
}

function estimateRun(selectedModels, caseText, referenceSummary) {
  const inputTokens = estimateTokens(caseText) + estimateTokens(referenceSummary) + 280;
  const outputTokens = 760;

  let max_usd = 0;
  for (const model of selectedModels) {
    const pricing = PRICE_PER_1K[model.provider] || PRICE_PER_1K.openai;
    max_usd += (inputTokens / 1000) * pricing.input;
    max_usd += (outputTokens / 1000) * pricing.output;
  }

  max_usd *= 1.25;

  return {
    input_tokens: inputTokens * selectedModels.length,
    output_tokens: outputTokens * selectedModels.length,
    total_tokens: (inputTokens + outputTokens) * selectedModels.length,
    max_usd: Number(max_usd.toFixed(4)),
  };
}

function randomId(size) {
  return crypto.randomBytes(size).toString('hex');
}

function buildPrompt(caseText, referenceSummary) {
  return [
    'Task: Summarize the following case text faithfully.',
    'Requirements:',
    '- Keep key holdings, constraints, and outcomes.',
    '- Do not invent facts.',
    '- Keep output concise (120-220 words).',
    '',
    referenceSummary
      ? `Reference summary (for grounding):\n${referenceSummary}\n`
      : 'Reference summary: not provided. Use case text only.\n',
    `Case text:\n${caseText}`,
  ].join('\n');
}

async function executeRun({ run_id, caseText, referenceSummary, selectedModels, keys, runMode }) {
  const run = runs.get(run_id);
  if (!run) return;

  run.status = 'running';
  run.started_at = Date.now();

  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Run exceeded hard timeout (10 minutes).')), RUN_TIMEOUT_MS);
  });

  const jobPromise = (async () => {
    const modelResults = [];
    const warnings = [];
    const baselineScoreMode = runMode === RUN_MODE_STUDY || referenceSummary ? 'full' : 'provisional';

    for (const modelEntry of selectedModels) {
      const adapter = PROVIDERS[modelEntry.provider];
      if (!adapter) {
        modelResults.push({
          provider: modelEntry.provider,
          model: modelEntry.model,
          score_mode: baselineScoreMode,
          summary_text: '',
          error: 'Provider is not supported by local runner.',
          pillars: {
            nli: { value: null, confidence: 0 },
            judge: { value: null, confidence: 0 },
            coverage: { value: null, confidence: 0 },
          },
          composite_score: null,
          composite_confidence: 0,
        });
        continue;
      }

      try {
        const output = await adapter({
          apiKey: keys[modelEntry.provider],
          model: modelEntry.model,
          prompt: buildPrompt(caseText, referenceSummary),
          timeoutMs: 90_000,
        });

        const summaryText = normalizeText(output.text, 8000);
        const pillars = evaluatePillars({
          caseText,
          referenceSummary,
          summaryText,
        });
        const composite = buildComposite(pillars);

        if (composite.warnings.length) warnings.push(...composite.warnings);

        modelResults.push({
          provider: modelEntry.provider,
          model: modelEntry.model,
          score_mode: composite.score_mode,
          summary_text: summaryText,
          error: null,
          pillars,
          composite_score: composite.composite_score,
          composite_confidence: composite.composite_confidence,
          weights_used: composite.weights_used,
          usage: output.usage || null,
        });
      } catch (error) {
        modelResults.push({
          provider: modelEntry.provider,
          model: modelEntry.model,
          score_mode: baselineScoreMode,
          summary_text: '',
          error: toUserFacingError(error),
          pillars: {
            nli: { value: null, confidence: 0 },
            judge: { value: null, confidence: 0 },
            coverage: { value: null, confidence: 0 },
          },
          composite_score: null,
          composite_confidence: 0,
        });
      }
    }

    modelResults.sort((a, b) => {
      const aScore = Number.isFinite(a.composite_score) ? a.composite_score : -1;
      const bScore = Number.isFinite(b.composite_score) ? b.composite_score : -1;
      return bScore - aScore;
    });

    return {
      score_mode: baselineScoreMode,
      non_comparability_note:
        runMode === RUN_MODE_STANDARD && !referenceSummary
          ? 'No reference summary was provided, so this run is provisional and not directly comparable to leaderboard scores.'
          : null,
      warnings: [...new Set(warnings)],
      models: modelResults,
      generated_at: new Date().toISOString(),
    };
  })();

  const result = await Promise.race([jobPromise, timeoutPromise]);
  run.status = 'completed';
  run.result = result;
  run.completed_at = Date.now();
}

function toUserFacingError(error) {
  const text = String(error?.message || '').toLowerCase();
  if (text.includes('aborted')) return 'Provider request timed out.';
  if (text.includes('401') || text.includes('403') || text.includes('api key')) {
    return 'Provider rejected credentials. Check API key and model access.';
  }
  return 'Provider call failed for this model.';
}
