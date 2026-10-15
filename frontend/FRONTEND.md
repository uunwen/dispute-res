# RumblePaws Frontend

Multi-agent ride-hailing dispute resolution UI. Built with React + TypeScript + Vite.

## Quick start

```bash
cd frontend
npm install
npm run dev          # start the dev server (http://localhost:5173)
npm run build        # production build → dist/
npm run lint         # oxlint
```

The frontend talks to the FastAPI backend at `/api` (proxied by Vite in dev).
Postgres and Redis must be running (see `../backend` README), or use sample-data
mode (below).

## Sample-data mode

Set `VITE_USE_MOCK=true` to run the frontend without a backend. Every API call
returns in-memory sample data (12 disputes, 6 trips, evidence, GPS, chat logs).
A grey banner at the top indicates when sample-data mode is active.

```bash
# sample-data mode (no backend needed)
VITE_USE_MOCK=true npm run dev

# real backend mode (default)
npm run dev
```

For a production build with sample data:

```bash
VITE_USE_MOCK=true npm run build
```

The `VITE_USE_MOCK` value is baked in at build time. To switch modes, rebuild.

## Pages

| Route | Screen | Description |
|---|---|---|
| `/` | Dashboard | Welcome card, 4 stat tiles, recent disputes table |
| `/new` | File a Dispute | 4-step wizard: Details → Evidence → Review → Submit |
| `/disputes` | Disputes | Filterable/sortable table + analytics pane (wide screens) |
| `/disputes/:id/debate` | Debate | Multi-agent debate playback with rounds + transcript |
| `/disputes/:id/ruling` | Ruling | Final ruling (resolved) or escalation (human review) |
| `/disputes/:id/evidence` | Evidence | Trip evidence, policy rules, analysis tabs |
| `/disputes/:id/arguments` | Arguments | Side-by-side rider/driver advocate arguments |
| `/analytics` | Analytics | Stat tiles, disputes-by-category bars, outcomes breakdown |
| `/policies` | Policies | Searchable list of policy rules grouped by part |
| `/agent-logs` | Agent Logs | Table of agent runs + trace drawer with per-agent output |
| `/settings` | Settings | Model assignments, policy version, sample-data indicator |

Navigation is via the sidebar. Below 1100px the sidebar collapses to icons.

## Architecture

- `src/main.tsx` — entry point, renders `NewApp`
- `src/NewApp.tsx` — shell: sidebar + topbar + screen router
- `src/api.ts` — data layer. Swaps between real fetch calls and the mock layer
  based on `VITE_USE_MOCK`. Exports `isMockMode` for the banner.
- `src/mocks/` — sample-data fixtures and mock API implementation
- `src/pages/` — one file per screen
- `src/components/` — shared components (Sidebar, TopBar, StatusBadge, etc.)
- `src/lib/` — pure helpers (rounds, status, rules, category metadata)
- `src/hooks/` — `useDisputeStream` (SSE + polling), `useReducedMotion`
- `src/styles/` — base CSS tokens and layout

## Key constraints

- No fabricated numbers. Every stat, confidence, and refund comes from the data
  layer. Missing values render as `—`.
- No fabricated agent text. The debate, arguments, and agent logs pages show
  verbatim `brief.argument_summary` from the backend.
- `VITE_USE_MOCK=false` must work: no code path depends on sample data existing.
  The mock layer is lazily imported only when `VITE_USE_MOCK === 'true'`.
