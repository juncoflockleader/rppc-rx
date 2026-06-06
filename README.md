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
    repositories/   raw-SQL data access (migrations are the schema source of truth)
    services/       storage + job-queue abstractions
    workers/        background worker entrypoint + job handlers
  migrations/       numbered SQL migrations for the 19-table schema (§8)
  personas/         versioned persona seed assets (YAML, §15)
docs/               design notes
```

## Milestone 1 status (Skeleton)

Per design §25 Milestone 1, this skeleton delivers:

- [x] Project CRUD (`/api/projects`)
- [x] Source upload + text paste (`/api/projects/{id}/sources`)
- [x] Object storage abstraction (local-filesystem backend for MVP)
- [x] Job table + job-queue abstraction + worker skeleton
- [x] Progress API (`GET /api/jobs/{id}`, SSE `GET /api/jobs/{id}/events`)
- [x] Minimal auth (dev bearer-token stub — replace before beta)

Source *processing*, persona generation, script/QA/audio pipelines are later
milestones — their job types are registered as stubs so the queue path is exercisable.

## Quick start

```bash
cd backend
cp .env.example .env                 # edit DATABASE_URL etc.
python -m venv .venv && source .venv/bin/activate
pip install -e .

# create the schema
psql "$DATABASE_URL" -f migrations/000_apply_all.sql      # or run files 001..010 in order

# run the API
uvicorn app.main:app --reload

# in another shell: run a worker
python -m app.workers.worker
```

Without Postgres/Redis the app still imports; the queue falls back to an
in-process thread worker (see `app/services/queue.py`) so the skeleton runs
out of the box for local demos.

## Configuration

All config is environment-driven (design §24.2). See `backend/.env.example`.
Secrets never live in the frontend or in source.
