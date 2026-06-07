# Podcast Synthesis (rppc-rx)

Turn uploaded material into a multi-character philosophical podcast, where versioned
*personas* (Laozi, Buddha, Modern Host …) discuss the user's source with citable
evidence, segment-level scripts, and per-segment audio re-rendering.

See the specs:

- `Podcast_Synthesis_PRD_v0.1.docx`
- `Podcast_Synthesis_MVP_Technical_Design_v0.1.docx`
- `docs/design-critique.md` — gaps / risks / sequencing notes

## Repo layout

```
backend/            FastAPI service (Python — preferred per design §7)
  app/
    api/            HTTP routers (projects, sources, personas, jobs)
    providers/      LLM + embedding provider adapters (fake / anthropic / openai)
    ingestion/      parse → chunk → analyze (summary/claims) → embed pipeline
    repositories/   raw-SQL data access (migrations are the schema source of truth)
    services/       storage + job-queue abstractions
    workers/        background worker entrypoint + job handlers
  migrations/       numbered SQL migrations for the 19-table schema (§8)
  personas/         versioned persona seed assets (YAML, §15)
  tests/            unit (no DB) + integration (needs Postgres)
docs/               design notes
docker-compose.yml  local Postgres (pgvector) + Redis
Makefile            db-up / migrate / run / test ...
ci/ci.yml           CI workflow (move to .github/workflows/ to enable — see ci/README.md)
```

## Milestone 1 status (Skeleton) — complete

Per design §25 Milestone 1, runnable and tested:

- [x] Project CRUD (`/api/projects`)
- [x] Source upload + text paste (`/api/projects/{id}/sources`), storage uri persisted
- [x] Object storage abstraction (local-filesystem backend; prefix-cleanup on delete)
- [x] Job table + job-queue abstraction + worker skeleton (inproc + rq)
- [x] Progress API (`GET /api/jobs/{id}`, SSE `GET /api/jobs/{id}/events`)
- [x] Minimal auth (dev bearer-token stub — real JWT deferred to M8)
- [x] Business-event logging (§20.1), source size limit (§22.3), human-readable errors (§18)
- [x] Unit + integration tests, GitHub Actions CI

## Milestone 2 status (Source Processing) — complete

Per design §25 M2, a source now becomes structured, retrievable data:

- [x] Document parser — text/md passthrough, PDF via `pypdf` with page tracking (§11.1)
- [x] Chunker — ~600–1000 tokens, 100–150 overlap, char/page offsets (§27)
- [x] LLM provider adapter (§13) — `fake` (deterministic, default) + `anthropic` + `openai`,
      with schema-validated structured output and repair/retry (§13.4)
- [x] Embedding provider adapter — `fake` (deterministic) + `openai`
- [x] Source summary + theme extraction; claim extraction with chunk/page links (§11.1)
- [x] `project_source` vector index in pgvector + cosine retrieval (§10)
- [x] `GET /api/sources/{id}/summary` (§12.2)
- [x] Unit + integration tests on fake providers (no network)

## Milestone 3 status (Persona Asset) — complete

Per design §25 M3, personas are versioned DB assets with a canon index:

- [x] Persona import — YAML seeds → `persona_assets` / `persona_versions` (idempotent upsert)
- [x] `persona_canon` index (migration 012) — bundled public-domain excerpts
      (Tao Te Ching/Legge, Dhammapada/Müller) chunked + embedded per version (§10)
- [x] Canon retrieval — `search_canon(version_id, query_vec, k)` cosine search
- [x] DB-backed persona library API (`/api/personas`, `/api/personas/{id}/versions/{v}`)
- [x] Persona usability/safety guard (§19.1) — status + prohibited-type checks
- [x] `make seed-personas` (run after `make migrate`)
- [x] Unit + integration tests (import, canon retrieval, idempotency, API, safety)

Seed the library after migrating:

```bash
make seed-personas        # python -m app.personas_import
```

## Milestone 4 status (Episode Planning) — complete

Per design §25 M4 / §11.2–11.4 — the first stage that uses M2 claims *and* M3 canon:

- [x] Episode create with participants + persona safety check (`POST /api/projects/{id}/episodes`)
- [x] Role context cards (§11.3) — per speaker, grounded in project claims + persona canon
- [x] Discussion plan (§11.4, §14.1) — beats, speakers, target seconds, claim/concept links
- [x] Background `episode_planning` job (role context → plan) with progress
- [x] Get plan / get role context / regenerate (new plan version) (`/api/episodes/...`)
- [x] `role_context_cards` table (migration 013), versioned for regeneration
- [x] Unit + integration tests (generators, full create→plan flow, regenerate, validation)

## Milestone 5 status (Script Studio) — complete

Per design §25 M5 / §11.5 — discussion plan → editable segment-level script:

- [x] Script generation (background `script_generation` job): plan + role context
      cards + claims → segments, one speaker each, host owns modern terms (§11.5)
- [x] Segment-level storage (§4.2) with per-segment **evidence links** (§8.14) —
      source_material links validated against real claims, else `needs_review`
- [x] Per-speaker second estimates (§27.1) + speaker-share metadata
- [x] Script versioning; `GET /api/episodes/{id}/scripts/latest` with evidence
- [x] Segment edit (`PATCH`) and LLM rewrite (`POST .../rewrite`) — re-estimated, marked `edited`
- [x] Unit + integration tests (generator/estimate, full generate→edit→rewrite flow)

## Milestone 6 status (Script QA) — complete

Per design §25 M6 / §11.6–11.7 — quality review made explicit and gated:

- [x] Seven QA dimensions over a script (background `script_qa` job):
      source-grounding (LLM entailment), persona-fidelity (LLM), **distinctiveness
      (engineered embedding proxy)**, anachronism, safety, dialogue-quality, audio-readiness
- [x] Per-segment warnings; high-severity findings flag segments `needs_review`
- [x] First-class **safety gate** `script_versions.safety_status` (migration 014) — `high_risk`
      blocks audio in M7 (§19.5)
- [x] QA panel API (`POST/GET /api/scripts/{id}/qa`) + rolled-up `qa_summary`
- [x] One-click repair (`POST /api/scripts/{id}/repair`) — LLM-rewrites flagged segments (§11.7)
- [x] Unit + integration tests (each check, panel, anachronism→repair, safety gate)

Two M0-critique items are now addressed: distinctiveness is *measured* (centroid
separation), not just LLM-scored; and source-grounding does entailment, not just
"does the claim id resolve."

## Milestone 7 status (Audio) — complete

Per design §25 M7 / §11.8–11.9 — voice direction → TTS → mix → export:

- [x] TTS provider adapter — deterministic `FakeTTSProvider` (valid WAV silence,
      no network/ffmpeg) + interface for real vendors
- [x] Voice direction (rule-based from each persona's voice_profile) → segment delivery
- [x] Per-segment TTS → `audio_segments`; stdlib-`wave` stitch (with pauses) → `audio_mixes`
- [x] **Safety gate (§19.5)** — `safety_status == high_risk` blocks render (API 409 + pipeline guard)
- [x] Single-segment re-render; **edit/rewrite/repair mark audio + mix stale** (M0-critique fix)
- [x] Get-latest + WAV download endpoints
- [x] Unit + integration tests (TTS/mixer/voice-direction, render→download, re-render+staleness, gate)

## Milestone 8 status (Beta Polish) — complete

Per design §25 M8 (backend subset; onboarding/admin UI are frontend):

- [x] Export package (`export_package` job) — transcript.md / .srt / show_notes.md /
      evidence_report.json + audio, zipped to storage; disclaimer embedded (§19.2)
- [x] Cost + debug-trace logging (`usage_events`) via recording decorators over the
      LLM/TTS providers, attributed per job; `GET /api/episodes/{id}/cost` (§20.3-20.4)
- [x] Feedback events (`POST /api/feedback`) (§8.19)
- [x] Privacy/copyright notices (`GET /api/meta/notices`, EN+ZH disclaimer) (§19.2-19.3)
- [x] Consistent error envelope `{error:{type,message}}` (§18); admin debug endpoint
- [x] Unit + integration tests (builder, export→zip download, cost, feedback, notices, errors)

**All eight MVP backend milestones are complete** — the full pipeline runs source →
claims → personas → episode → plan → script → QA → audio → export, verified by 88
tests (58 unit + 30 integration) against a real pgvector Postgres in CI.

## Frontend (in progress) — vertical slice

`frontend/` is a Next.js 16 (App Router) + TypeScript + Tailwind app. First slice:

- [x] Typed API client (`src/lib/api.ts`) with the dev bearer token + error-envelope unwrap
- [x] Job-polling hook (`useJob`) for live progress
- [x] Projects list + create (`/projects`)
- [x] Project detail (`/projects/[id]`) — add text/upload source, process with live
      progress, view source summary (themes + key claims)
- [x] Personas library (`/personas`) — cards + expandable stance/forbidden-moves detail
- [x] Episode creation (host + 1–2 guests, goal, length) from the project page
- [x] Outline screen (`/episodes/[id]`) — generate/regenerate plan with live progress,
      role-context cards, discussion-plan beats + takeaway
- [ ] Script editor (evidence/QA badges), audio player, export

Run it:

```bash
cd frontend
cp .env.example .env.local          # NEXT_PUBLIC_API_BASE + NEXT_PUBLIC_DEV_TOKEN
npm install && npm run dev          # http://localhost:3000 (backend must be on :8000)
```

The client contract is smoke-tested against a live backend via
`scripts/smoke_frontend_api.sh`. Remaining screens extend this slice incrementally.

## Quick start

```bash
make db-up                 # start Postgres (pgvector) + Redis via docker compose
make migrate               # apply migrations/000_apply_all.sql
make install               # pip install -e backend[dev,queue]  (use a venv)
make run                   # uvicorn app.main:app --reload
```

Then, with the dev bearer token (`DEV_BEARER_TOKEN`, default `dev-token`):

```bash
curl -s localhost:8000/api/projects -H 'Authorization: Bearer dev-token' \
     -H 'Content-Type: application/json' -d '{"title":"Desire"}' -X POST
```

The default `inproc` job queue runs handlers inside the API process, so no
separate worker is needed for local demos. Set `JOB_QUEUE_BACKEND=rq` and run
`make worker` to execute jobs off-process.

## Tests

```bash
make test-unit             # no database required
make test-integration      # needs a disposable Postgres (TEST_DATABASE_URL or DATABASE_URL)
make test                  # both
```

Integration tests rebuild the schema from migrations (DROP/CREATE SCHEMA public)
and truncate between tests — point them at a throwaway database. CI runs the full
suite against a `pgvector/pgvector:pg16` service container on every push.

## Configuration

All config is environment-driven (design §24.2). See `backend/.env.example`.
Secrets never live in the frontend or in source.
