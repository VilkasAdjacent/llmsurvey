# llmsurvey — Codebase Guide

**What it does:** Given a survey (questions + real published response distributions) and a demographic profile, `llmsurvey` generates synthetic participants sampled from real demographic proportions, prompts LLMs to answer as those personas via the Replicate API, and compares the resulting distributions to ground truth using statistical metrics.

---

## High-level architecture

```
surveys/<name>/          ← survey data (YAML) + run outputs (JSON/PNG)
templates/               ← Jinja2 prompt templates
llmsurvey/               ← Python package
frontend/                ← React + TypeScript SPA (Vite)
```

The CLI (`llmsurvey run`) is the primary entry point. The FastAPI server (`llmsurvey serve`) exposes the survey/run data as a REST API and optionally serves the built React app.

---

## Python package map

| File | Responsibility |
|------|----------------|
| [llmsurvey/cli.py](llmsurvey/cli.py) | Click commands: `run`, `stats`, `report`, `serve`, `new` |
| [llmsurvey/models/survey.py](llmsurvey/models/survey.py) | Pydantic: `Survey`, `Question`, `RealDistribution` |
| [llmsurvey/models/participant.py](llmsurvey/models/participant.py) | Pydantic: `SyntheticParticipant` |
| [llmsurvey/models/results.py](llmsurvey/models/results.py) | Pydantic: `RawResponses`, `RunResults`, `RunStats`, `ModelQuestionStats` |
| [llmsurvey/demographics.py](llmsurvey/demographics.py) | Stratified participant sampler from demographic YAML |
| [llmsurvey/llm.py](llmsurvey/llm.py) | Replicate API wrapper, prompt rendering, response caching, fuzzy parsing |
| [llmsurvey/compare.py](llmsurvey/compare.py) | `aggregate_results` + `compute_stats` (chi-square, KL, JS divergence) |
| [llmsurvey/report.py](llmsurvey/report.py) | LLM-generated narrative summary via Replicate |
| [llmsurvey/viz.py](llmsurvey/viz.py) | Matplotlib/Seaborn charts → PNG files |
| [llmsurvey/server.py](llmsurvey/server.py) | FastAPI app factory — 4 REST endpoints + optional static serving |

---

## Data flow for `llmsurvey run`

1. **`demographics.py`** — reads `demographic.yaml`, samples N `SyntheticParticipant` objects using seeded weighted random draws (always `manual_distribution`; the `CensusClient` class exists but Census API queries are not currently wired into the run path)
2. **`llm.py`** — renders a Jinja2 prompt per (participant × question × model), calls Replicate in parallel (`ThreadPoolExecutor`, 8 workers), caches responses as `.cache/<sha256>.txt`, fuzzy-matches raw output to a valid option
3. **`compare.py`** — `aggregate_results` computes per-model response distributions; `compute_stats` computes chi-square p-value, KL divergence, JS divergence, per-option delta, parse failure rate, and a heuristic bias direction label
4. **`viz.py`** — writes PNG charts to `runs/<run_id>/charts/`
5. **`report.py`** — calls `anthropic/claude-opus-4.6` via Replicate with the results/stats JSON to produce a prose summary

All intermediate and final outputs are written as JSON into `surveys/<name>/runs/<run_id>/`:
`responses.json` → `results.json` → `stats.json` → `summary.json`

---

## Key design decisions

**Caching by content hash** — `llm.py` caches Replicate responses as `.cache/<sha256(model+prompt)>.txt`. Re-running the same survey is free. Disable with `--no-cache`.

**Fuzzy response parsing** — LLMs don't always return an exact option string. `parse_response` tries exact match → `difflib.get_close_matches` (cutoff 0.6) → substring match. Unresolvable responses are recorded as `parsed: null` and excluded from distributions; the failure rate is tracked in `stats.json`.

**Parallelism** — all (model × question × participant) tasks run concurrently via `ThreadPoolExecutor`. The Replicate SDK is thread-safe.

**App factory pattern** — `server.py` exposes `create_app(surveys_dir, dist_dir)` rather than a module-level app, so the CLI and tests can inject paths. The React build is mounted only if `frontend/dist/` exists, so the server works as API-only without a build step.

**Single-port prod deployment** — `llmsurvey serve` runs FastAPI + static file serving on one port. In dev, Vite proxies `/api` → `:8000`.

---

## Where to look when modifying things

| Task | Start here |
|------|-----------|
| Add/change a survey question type | [llmsurvey/models/survey.py](llmsurvey/models/survey.py) (`Question.type` literal), then [llmsurvey/compare.py](llmsurvey/compare.py) |
| Change how participants are generated | [llmsurvey/demographics.py](llmsurvey/demographics.py) — `sample_participants` and the `_*_LABELS` / `_*_RANGES` dicts |
| Change the prompt sent to LLMs | [templates/survey_prompt.j2](templates/survey_prompt.j2) — or pass `--template` on the CLI |
| Add a new statistical metric | [llmsurvey/compare.py](llmsurvey/compare.py) + [llmsurvey/models/results.py](llmsurvey/models/results.py) (`ModelQuestionStats`) |
| Change which model generates the narrative | [llmsurvey/report.py](llmsurvey/report.py) — `_SUMMARY_MODEL` constant |
| Add a new CLI command | [llmsurvey/cli.py](llmsurvey/cli.py) |
| Add a new API endpoint | [llmsurvey/server.py](llmsurvey/server.py) |
| Change chart appearance | [llmsurvey/viz.py](llmsurvey/viz.py) |
| Change the frontend chart | [frontend/src/components/QuestionChart.tsx](frontend/src/components/QuestionChart.tsx) (Recharts `BarChart`) |
| Add a new frontend page | [frontend/src/pages/](frontend/src/pages/) + route in [frontend/src/App.tsx](frontend/src/App.tsx) |
| Change TypeScript types (must match Python JSON) | [frontend/src/api/types.ts](frontend/src/api/types.ts) |

---

## Deployment

| File | Purpose |
|------|---------|
| [Dockerfile](Dockerfile) | Multi-stage build — Node builds the React frontend, Python image runs the server |
| [.dockerignore](.dockerignore) | Excludes `.venv/`, `surveys/`, build artifacts from the image |
| [fly.toml](fly.toml) | fly.io config — 512MB shared VM, auto-stop, 1GB volume at `/data` |
| [deploy.py](deploy.py) | `uv run deploy.py [setup \| deploy \| publish \| pull]` — fly.io helpers |
| [.github/workflows/deploy.yml](.github/workflows/deploy.yml) | Auto-deploys to fly.io on push to `main` (requires `FLY_API_TOKEN` secret) |

`surveys/` is **not** baked into the image — it lives on a persistent fly.io volume (`/data/surveys`). Push new run results with `uv run deploy.py publish`.

---

## Survey data format

`surveys/<name>/survey.yaml` — questions with `real_distribution.overall` (required) and optional demographic slices (`by_party`, `by_age`, etc.)

`surveys/<name>/demographic.yaml` — flat `manual_distribution` dict with probability weights for age buckets, gender, race, education, income, and party. Keys are the fixed set in `demographics.py`; adding a new demographic axis requires changes there.

New survey: `llmsurvey new <name>` scaffolds both YAML files with commented templates.
