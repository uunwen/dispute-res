# 1. Infra (Postgres + Redis) — must be up before alembic

docker compose up -d

# 2. Config — config.py reads .env from the backend working dir

# copy the template and fill in API keys

copy ..\.env.example .env # (from backend/ dir)

# 3. Install deps

uv sync

# (for running tests: uv sync --group dev)

# 4. Create tables + vector extension (all migrations)

uv run alembic upgrade head

# 5. Seed sample data (accounts/trips/disputes)

uv run python scripts/seed.py

# 6. Ingest policies into pgvector (needed or dispute resolution fails)

uv run python scripts/ingest_policies.py

# 7. Run

uv run uvicorn app.main:app --reload

# separate terminal

uv run python scripts/worker.py

uv run python scripts/resolve_all.py
