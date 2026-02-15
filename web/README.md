# ∑VAL Web

High-contrast ASCII-brutalist Next.js frontend for the ∑VAL AI summarization benchmark.

## Quick Start

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Main Routes

- `/` leaderboard
- `/explore` per-case explorer
- `/reliability` judge reliability
- `/methodology` benchmark method
- `/why-it-matters` non-technical explainer
- `/run-your-case` BYOK local simulation

## Run Your Case (Local BYOK)

This feature lets users:

- submit their own case text or upload files (`.txt`, `.md`, `.pdf`)
- provide their own provider API keys
- select up to 3 models
- run scoring locally through a localhost runner

### Start local runner

```bash
npm run runner:quickstart
```

Runner URL default: `http://127.0.0.1:8787`.

### Data + Key Handling

- Keys stay in local runner memory only.
- Keys are never persisted to disk by the runner.
- Session delete clears keys and run artifacts.
- Auth between web UI and runner uses `X-Session-Id` and `X-Csrf-Token` headers.
- Provider APIs still receive submitted case text for generation.

### Study Mode

- Use `study` mode for formal evaluations.
- Study mode requires a reference summary so all runs use full 3-pillar scoring and remain comparable.
- `standard` mode allows missing reference summaries, but scores become provisional and non-comparable to leaderboard runs.

Detailed docs: `docs/run-your-case.md`.

## Quality Checks

```bash
npm run lint
npm run build
```
