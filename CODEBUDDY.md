# CODEBUDDY.md

## Goal

Multi-agent ride-hailing dispute resolution system (hackathon MVP).

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.0 (async)
- Alembic
- Pydantic v2
- Postgres with pgvector
- Redis
- Managed with uv
- Run FastAPI locally with `uv run`; only Postgres and Redis run in Docker
- Frontend (later) uses bun

## Dev Machine

Windows. Use cross-platform commands and `pathlib`.

## Architecture Rules

1. One FastAPI app. Agents (RiderAdvocate, DriverAdvocate, Judge) are separate
   modules under `app/agents/` behind clean interfaces, called by an orchestrator.
2. Deterministic Python code computes ALL numbers (distance, deviation, fare,
   refund). The LLM never does math.
3. Every piece of computed evidence is an `EvidenceItem` with a unique id.
   Agents must cite evidence ids; the Judge validates the citations exist.
4. Every inter-agent message is saved to an `agent_messages` table and published
   to Redis so it can be streamed to the UI.
5. LLM access goes through one wrapper (`app/llm/client.py`) that is configurable
   via env vars (base URL, API key, model) and supports structured output
   via Pydantic schemas.
6. Policy text and hard rules are placeholders to be refined later.
7. Demographics may only change the TONE of the response, never the ruling.

## Layout

- `backend/app/{api,agents,evidence,rules,rag,llm,db,orchestrator,schemas}`
- `backend/tests/`
- `backend/scripts/`
- `backend/policies/`
- `backend/data/`
