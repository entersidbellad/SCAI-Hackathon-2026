# Run Your Case (BYOK Local Simulation)

## Goal

Enable users to run ∑VAL-style scoring with their own case text and own API keys, while keeping keys local.

## Local Runner Setup

From project root:

```bash
npm run runner:quickstart
```

This starts the local runner at:

- `http://127.0.0.1:8787`

## Security Model

- Runner binds to localhost (`127.0.0.1`) only.
- API keys are kept in process memory only (session-scoped, no disk persistence).
- Keys are never returned in API responses.
- Session cleanup clears keys and run artifacts.
- Session auth is header-based (`X-Session-Id`, `X-Csrf-Token`).

## Disclaimer

- Your API keys are sent only to your local runner (`127.0.0.1`) and kept in memory for this session.
- They are not stored by ∑VAL cloud services.
- Model providers still receive submitted text for generation.
- Results are decision-support signals, not legal advice or absolute truth.

## Supported Providers (v1)

- OpenAI
- Anthropic
- Gemini
- OpenRouter

Custom model IDs are supported. You can select preset models or add your own provider/model slug entries (up to 3 total models per run).

## File Inputs

- `.txt`
- `.md`
- `.pdf`

Max file size: 10MB.

## Scoring Modes

- `standard`: reference summary optional.
- `study`: reference summary required.

Study mode requirement:

- Study mode requires a reference summary so all runs use full 3-pillar scoring and remain comparable.

Pillar weights:

- NLI: `0.35`
- Judge: `0.40`
- Coverage: `0.25`

## API Endpoints

- `GET /health`
- `POST /session/start`
- `POST /files/parse`
- `POST /runs` (accepts `run_mode: "standard" | "study"`)
- `GET /runs/:run_id`
- `DELETE /session/:session_id`

## Run Limits (Conservative Defaults)

- Max 3 models per run
- One case per run
- Input token cap enforced
- 10-minute hard timeout

## Cost Estimate Notes

- The pre-run estimate is a conservative upper bound.
- For custom model IDs and OpenRouter routes, actual billing may vary by provider/model route.
