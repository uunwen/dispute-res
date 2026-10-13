# Dispute Resolver — Frontend

Single-page UI for the multi-agent ride-hailing dispute resolver. Built with
Bun, Vite, React and TypeScript (no component library, plain CSS).

## Prerequisites

- [Bun](https://bun.sh) (>= 1.0)
- The backend running on `http://localhost:8000`:
  `cd ../backend && uv run uvicorn app.main:app --reload`

## Setup

```bash
bun install
```

## Run

```bash
bun dev
```

Then open http://localhost:5173. In development, `/api/*` requests are proxied
to `http://localhost:8000` (see `vite.config.ts`).

## Build

```bash
bun run build
```

## Notes

- Map tiles load from OpenStreetMap; an internet connection is required to
  render the route map.
- The agent conversation streams live over Server-Sent Events
  (`GET /disputes/{id}/stream`).
