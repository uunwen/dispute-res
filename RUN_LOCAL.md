# Run the Project Locally (Windows / PowerShell)

Exact steps to run the entire dispute-resolution system from scratch on Windows.
All commands are PowerShell. Paths use backslashes.

---

## 1. Prerequisites

| Dependency | Why | How to get it |
|---|---|---|
| **Docker Desktop** (or Docker Engine + `docker compose`) | Runs Postgres + Redis in containers | [docker.com](https://www.docker.com/products/docker-desktop) |
| **Python 3.12+** | Backend runtime | [python.org](https://www.python.org/downloads/) |
| **uv** (Python package manager) | Installs backend deps and runs the app | `pip install uv` or [astral.sh/uv](https://docs.astral.sh/uv/) |
| **Bun** (JavaScript runtime) | Frontend dev server | [bun.sh](https://bun.sh/) |

### What Docker starts

`docker-compose.yml` (repo root) starts **two** services:

- **`db`** — `pgvector/pgvector:pg16` image (Postgres 16 with the pgvector extension pre-installed). Exposed on host port **5433** (container port 5432). Database name: `dispute_resolver`. User/password: `postgres` / `postgres`.
- **`redis`** — `redis:7-alpine`. Exposed on host port **6379**.

You do **not** need to install PostgreSQL or Redis natively — Docker provides both. The pgvector extension is already in the image; the migration / `init_db.py` script will `CREATE EXTENSION IF NOT EXISTS vector` for you.

Start them:

```powershell
# from the repo root
docker compose up -d
```

Verify:

```powershell
docker compose ps
```

Both `dispute-resolver-db` and `dispute-resolver-redis` should show status `healthy`.

---

## 2. Environment Variables

The backend reads settings via `pydantic-settings` from a `.env` file (`app/config.py`, `model_config = SettingsConfigDict(env_file=".env")`).

### Where the `.env` file goes

**Repo root** — the same folder as `docker-compose.yml`. The backend is started from `backend/`, but `uv run uvicorn` sets the working directory to `backend/`, so the `.env` must be at `backend/.env` OR at the repo root if you `cd` there first.

> **Simplest approach:** create `backend/.env` (copy from `.env.example` at the repo root). The `Settings` class looks for `.env` relative to the current working directory, which is `backend/` when you run `uv run uvicorn` from there.

```powershell
# from the repo root
Copy-Item .env.example backend\.env
```

Then edit `backend\.env` and fill in `LLM_API_KEY` (your Gemini API key).

### Every environment variable the backend reads

| Variable | Required? | Default (if omitted) | Notes |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:postgres@localhost:5433/dispute_resolver` | Must point to the Postgres from Docker. |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Must point to the Redis from Docker. |
| `LLM_BASE_URL` | No | `https://generativelanguage.googleapis.com/v1beta/openai/` | OpenAI-compatible endpoint (Gemini). |
| `LLM_API_KEY` | **Yes for real agent output** | (empty) | Without it, the backend starts but LLM calls fail and agents produce degraded/mock briefs. |
| `LLM_MODEL` | No | `gemini-2.5-flash` | |
| `LLM_MODEL_ADVOCATE` | No | (empty = defaults to `LLM_MODEL`) | |
| `LLM_MODEL_JUDGE` | No | (empty = defaults to `LLM_MODEL`) | |
| `LLM_MODEL_TOOLS` | No | (empty = defaults to `LLM_MODEL`) | |
| `LLM_MOCK` | No | `false` | If `true`, skips real LLM calls entirely. |
| `LLM_TIMEOUT` | No | `60.0` | |
| `LLM_MAX_RETRIES` | No | `3` | |
| `LLM_BACKOFF_BASE` | No | `0.5` | |
| `LLM_TEMPERATURE` | No | `0.0` | |
| `LLM_MAX_TOKENS` | No | (empty = no cap) | |
| `ADVOCATE_MAX_TOOL_CALLS` | No | `2` | |
| `REBUTTAL_ENABLED` | No | `true` | Whether advocates run a second rebuttal round. |
| `EMBEDDING_MODEL` | No | `gemini-embedding-001` | |
| `EMBEDDING_DIM` | No | `384` | Must match the fastembed model dimension. |
| `EMBEDDING_BASE_URL` | No | (empty) | |
| `EMBEDDING_API_KEY` | No | (empty) | **If empty, falls back to local `fastembed` model** (no API key needed). |
| `FASTEMBED_MODEL` | No | `BAAI/bge-small-en-v1.5` | Local model used when `EMBEDDING_API_KEY` is empty. |
| `EMBEDDING_SIMILARITY_CUTOFF` | No | `0.25` | |
| `ROUTE_BUFFER_M` | No | `100.0` | |
| `ROUTE_MIN_EXTRA_KM` | No | `2.0` | |
| `ROUTE_MIN_FRACTION_OUTSIDE` | No | `0.2` | |
| `ROUTE_TRAFFIC_SPEED_KMH` | No | `15.0` | |
| `STOP_DURATION_MIN` | No | `2.0` | |
| `NOSHOW_PROXIMITY_M` | No | `100.0` | |
| `NOSHOW_MIN_WAIT_MIN` | No | `5.0` | |
| `ABUSE_RISK_THRESHOLD` | No | `0.6` | |
| `ESCALATION_ENABLED` | No | `true` | |
| `ESCALATION_THRESHOLD` | No | `0.65` | |
| `FRAUD_DISPUTE_FREQUENCY_DAYS` | No | `30` | |
| `FRAUD_DISPUTE_FREQUENCY_THRESHOLD` | No | `3` | |
| `FRAUD_WIN_RATE_THRESHOLD` | No | `0.4` | |
| `FRAUD_REPEAT_DEVIATION_THRESHOLD` | No | `2` | |
| `FRAUD_ACCOUNT_AGE_DAYS` | No | `14` | |
| `FRAUD_PENALTY_THRESHOLD` | No | `0.5` | |
| `FRAUD_PENALTY_WEIGHT` | No | `0.2` | |
| `SLA_SAFETY_SECONDS` | No | `3600` | |
| `SLA_DEFAULT_SECONDS` | No | `86400` | |
| `EVAL_CONCURRENCY` | No | `3` | |

### Which are strictly required to boot

Only **`DATABASE_URL`** and **`REDIS_URL`** are required for the server to start. Both have working defaults that match the Docker setup, so if you use Docker Compose as-is, you don't even need to set them.

**`LLM_API_KEY`** is required for real agent debate text. Without it, the server still boots, but every LLM call degrades and agents produce fallback briefs ("No brief produced (LLM unavailable).").

**`EMBEDDING_API_KEY`** is optional — leave it empty and the backend uses the local `fastembed` model (`BAAI/bge-small-en-v1.5`, 384 dims). This is the recommended path for local development.

---

## 3. Database Setup

Run these from the `backend\` folder. Order matters.

### Step 3a — Apply migrations (creates all tables + pgvector extension)

```powershell
cd backend
uv run alembic upgrade head
```

This runs all 7 migrations in `alembic/versions/`:
1. `b1e2a3c4d5f6` — initial tables
2. `b8c9d0e1f2a3` — embedding space
3. `c2d3e4f5a6b7` — policy embedding unconstrained
4. `d4e5f6a7b8c9` — escalation
5. `e5f6a7b8c9d0` — consolidate dispute category
6. `f6a7b8c9d0e1` — add llm_degraded
7. `a7b8c9d0e1f2` — rulings model info

> **Note:** The `alembic/env.py` overrides `sqlalchemy.url` from `settings.database_url` at runtime, so the `sqlalchemy.url` line in `alembic.ini` is just a placeholder. Your `.env` (or the default) is what matters.

### Step 3b — Ingest policy documents (embeds markdown into pgvector)

```powershell
uv run python scripts/ingest_policies.py
```

This chunks every `*.md` file in `backend/policies/`, embeds each chunk (using fastembed locally, or the API if `EMBEDDING_API_KEY` is set), and inserts them into the `policy_chunks` table. The Judge and advocates retrieve these chunks via RAG during dispute resolution.

### Step 3c — Seed trips, disputes, and ground truth

```powershell
uv run python scripts/seed.py
```

This truncates all data tables, creates 10 riders + 10 drivers, generates 26 trips (with GPS traces, chat logs, fares), and files 26 disputes across 7 scenario types. It also writes `backend/data/ground_truth.json` with expected outcomes for evaluation.

> **Order:** migrations → ingest policies → seed. The seed script depends on the tables existing (migrations) and on the `policy_chunks` table being available (ingest runs independently, but the RAG retrieval during resolution needs it).

---

## 4. Start the API Server

```powershell
# from backend/
uv run uvicorn app.main:app --reload
```

- **Entry point:** `app.main:app` (the `app` object in `backend/app/main.py`)
- **Port:** `8000` (uvicorn's default)
- **`--reload`** enables hot-reload on file changes (useful for development)
- **CORS:** allows `http://localhost:5173` and `http://127.0.0.1:5173` (the frontend)
- **Docs:** `http://localhost:8000/docs` (Swagger) and `http://localhost:8000/redoc`

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## 5. Does the Worker Need to Run?

**Yes — if you want disputes filed through the UI to be resolved automatically.**

Here is why:

- **`POST /api/disputes`** (file a new dispute, called by the frontend wizard) only calls `enqueue_dispute()`. This puts the dispute ID into a Redis sorted set (`dispute_queue`). It does **not** resolve the dispute.
- **`scripts/worker.py`** is an infinite loop that calls `pop_dispute()` from the Redis queue and then calls `resolve_dispute()` on whatever it pops. **This is the only thing that drains the queue.**
- If you do **not** run the worker, disputes filed via the UI sit in the queue forever with status `open` and never get agent messages or a ruling.

> **Alternative:** `POST /api/disputes/:id/resolve` runs `resolve_dispute` as an in-process FastAPI `BackgroundTask` (no worker needed). But the UI's "New Dispute" flow does not call this — it only enqueues. So for the demo flow to work end-to-end, **the worker must be running.**

### Start the worker (separate terminal)

```powershell
# from backend/
uv run python scripts/worker.py
```

You should see it idle silently (no output until a dispute is enqueued). When a dispute is filed, it prints:

```
Resolving dispute 1 (priority 12345678.0)
```

> **Tip:** To resolve all open disputes in one shot without the worker, you can also run `uv run python scripts/resolve_all.py`. This is a one-shot script (not a loop) — it resolves every `open` dispute and exits.

---

## 6. Frontend Dev Proxy

`frontend/vite.config.ts`:

```js
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',   // ← the API port
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
},
```

- **Proxy target:** `http://localhost:8000` — **matches** the uvicorn port.
- **Path rewrite:** strips `/api` prefix. So `/api/disputes` → `http://localhost:8000/disputes`, which matches the backend routes (`@router.get("/disputes")` — routes are mounted at root, no `/api` prefix).
- **Frontend port:** `5173` (Vite default).

**The proxy is correctly configured. No changes needed.** If you see HTTP 502, it means the backend is not running on port 8000.

---

## 7. Final Checklist

You need **three** terminals open (plus Docker running in the background).

### Terminal 1 — Docker (Postgres + Redis)

```powershell
# repo root
docker compose up -d
```

**When it works:** `docker compose ps` shows `dispute-resolver-db` and `dispute-resolver-redis` both `Up (healthy)`.

### Terminal 2 — Backend API server

```powershell
cd backend
uv run uvicorn app.main:app --reload
```

**When it works:** prints `Uvicorn running on http://0.0.0.0:8000` and `Application startup complete.`. `http://localhost:8000/health` returns `{"status": "ok", ...}`.

### Terminal 3 — Worker (autonomous dispute resolution)

```powershell
cd backend
uv run python scripts/worker.py
```

**When it works:** runs silently (no output until a dispute is enqueued). When you file a dispute via the UI, it prints `Resolving dispute N (priority ...)`.

### Terminal 4 — Frontend dev server

```powershell
cd frontend
bun install   # first time only
bun run dev
```

**When it works:** prints `VITE vX.X ready in XXXms` and serves `http://localhost:5173`. Open it in your browser. The Disputes page loads without a 502.

### One-time setup (before opening Terminals 2-4)

```powershell
# 1. Start Docker services (Terminal 1)
docker compose up -d

# 2. Create .env from template
Copy-Item .env.example backend\.env
# Edit backend\.env and set LLM_API_KEY=<your Gemini key>

# 3. Install backend deps
cd backend
uv sync
cd ..

# 4. Apply migrations + ingest policies + seed
cd backend
uv run alembic upgrade head
uv run python scripts/ingest_policies.py
uv run python scripts/seed.py
cd ..

# 5. Install frontend deps
cd frontend
bun install
cd ..
```

### Quick verification

| Check | Expected |
|---|---|
| `docker compose ps` | 2 containers, both healthy |
| `http://localhost:8000/health` | `{"status": "ok", ...}` |
| `http://localhost:8000/docs` | Swagger UI loads |
| `http://localhost:5173` | RumblePaws dashboard loads, no 502 |
| File a dispute via UI | Terminal 3 (worker) prints `Resolving dispute N` |
| Open the dispute | Debate screen shows agent messages streaming in |
