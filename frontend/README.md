# OUTLIER frontend

Desktop-first web UI for the OUTLIER auction-intelligence backend (FastAPI). Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS v4 + lucide-react. No component library; native `fetch` through a small typed client in `lib/api.ts`.

## Run

```bash
# 1. backend (separate terminal)
cd backend && .venv/bin/python -m uvicorn outlier.main:app --port 8000
#    optional: load synthetic demo data
curl -X POST http://127.0.0.1:8000/api/demo/run

# 2. frontend
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build      # production build (type-checks everything)
npm start          # serve the production build on :3000
```

## Environment

| variable | default | purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE` | `http://127.0.0.1:8000` | base URL of the backend (no trailing slash). Image paths such as `/api/images/1` are resolved against it. |

Copy `.env.example` to `.env.local` to override.

## Pages

| route | what it does |
| --- | --- |
| `/` | Opportunity dashboard: system status pills, demo banner, filters (search / domain / tier / source / status / demo / watchlist / archived), sortable dense table, watch quick-action, empty state with "Load demo data". |
| `/items/[id]` | Item workspace: gallery (upload, URL fetch, lightbox), key metrics, score breakdown, watchlist + feedback; tabs for AI identification (evidence, discrepancies, clothing/jewelry detail, research queries, reference matches, correction form, run analysis, run log), comparables & valuation (sold vs active, inline edit, add/import/search, override/recalculate), finance what-if (scenarios, risk-adjusted, sensitivity grid), auction data (fields, snapshots, manual price update, edit), research notes & outcome. |
| `/watchlist` | Ending-soonest table with countdowns, current vs your max vs recommended bid, status, reminders, archive/remove, manual price update, due-reminder banner. |
| `/analytics` | KPIs, tiers by domain, categories, feedback counts, AI usage and daily budget bar. |
| `/settings` | Editable platform fees, acquisition/resale assumptions, thresholds, risk + ranking heuristics, analysis keywords, notifications, model pricing; read-only env + credential flags. Saves only changed sections. |
| `/import` | Manual form, CSV, Personal Shopper e-mail (.eml / HTML), saved item page; results with parsed preview and post-create photo upload. |
| `/reference` | Browse / search / add / edit / delete reference entries, load seed set. |
| `/jobs` | Background job list with retry and "process pending now". |

## Testing

`scripts/screenshot.mjs <path> <out.png>` captures a page from the dev server and reports console errors; `scripts/e2e.mjs <dir>` runs an interactive smoke test with Playwright (set `CHROME_PATH` if Chromium is not at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`). Both need the backend (with demo data) and `npm run dev` running.
