# OUTLIER — AI-powered auction intelligence & sourcing

OUTLIER finds under-described vintage clothing and jewelry on auction sites (ShopGoodwill first), identifies what
the items actually are from their photographs, researches resale value from **sold** comparables, computes
profitability and a maximum bid from real fees, and ranks opportunities on a research dashboard.

It is a local, single-user application: Python/FastAPI backend + SQLite, Next.js/TypeScript/Tailwind frontend.

> **Honesty rules built into the software**
> - Demo data is synthetic and is labelled `DEMO` everywhere (listings, images, comps, analysis runs).
> - Analysis runs only against a configured model provider; missing credentials produce setup instructions, never canned output.
> - Valuations use sold prices only. Active asking prices are shown as context and never substituted.
> - Unknown costs are reported as unknown, not silently treated as zero.
> - Ranking weights and risk adjustments are labelled as uncalibrated heuristics.

## Quick start

```bash
git clone <this repo> && cd Auction-Outliers
cp .env.example .env              # add ANTHROPIC_API_KEY and/or GEMINI_API_KEY for live analysis (optional for demo)

# backend (Python 3.11+, uv recommended: https://docs.astral.sh/uv/)
cd backend && uv venv .venv && VIRTUAL_ENV=.venv uv pip install -e ".[dev]"
.venv/bin/python -m uvicorn outlier.main:app --port 8000       # http://127.0.0.1:8000/docs

# frontend (Node 20+), in a second terminal
cd frontend && npm install && npm run dev                       # http://localhost:3000
```

Without `uv`: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`. With Docker: `docker compose up`.

Then open http://localhost:3000 and click **Load demo** (or `curl -X POST localhost:8000/api/demo/run`). The demo
imports seven synthetic auctions, runs the labelled demo analysis, attaches sample comps, computes finance and
ranks them. Demo listings (with their images, comps and runs) are removable with `DELETE /api/demo`. The run also
seeds ~25 *reference database* entries (makers, marks, characteristics with approximate 'typical' ranges labelled as
guidance, not comps); they are ordinary reference rows you can edit or delete at `/reference`.

Run the tests: `cd backend && .venv/bin/python -m pytest -q` (88 tests: finance, valuation, ranking, providers with
mocked SDKs, ingestion parsers, the model-output guards with adversarial JSON, input validation, and the full API
workflow incl. the spec's edge cases). Browser e2e: `cd frontend && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node scripts/e2e.mjs`
(27 steps against a running backend + frontend; adjust the browsers path for your machine).

## Analyzing your first real listing

1. **Get the listing in** (choose one):
   - *Capture bookmarklet*: install `tools/capture-bookmarklet.js` as a bookmark; on a ShopGoodwill item page you
     are viewing, click it. The page HTML is parsed locally (no model calls) and the item opens in OUTLIER. The
     backend allows the `shopgoodwill.com` origin by default so the bookmarklet can read the response
     (`OUTLIER_CORS_ORIGINS` to change). The page parser is best-effort until tuned on a real page (see Limitations).
   - *Import page*: save the item page (⌘S → "Webpage, HTML only") and upload it at `/import`.
   - *Manual form* at `/import`: title, URL, bid, shipping, handling, image URLs.
   - *Personal Shopper e-mail*: upload the `.eml` (or paste its HTML). Set `OUTLIER_IMAP_*` to poll your mailbox
     automatically (`POST /api/jobs {"job_type":"poll_email"}`).
   - *CSV / JSON*: `docs/samples/listings.csv`, `docs/samples/listings.json`.
2. **Photos**: image URLs are fetched automatically; or upload the listing photos on the item page. Deep analysis
   needs the full-size photos (e-mail thumbnails are not enough).
3. **Analyze**: on the item page click *Run analysis → auto*. Stage 1 (rules) → Stage 2 cheap vision triage
   (Gemini Flash / Claude Haiku) → Stage 3 deep identification (Claude Opus 5.5 by default, with a zoom tool that
   crops labels and hallmarks). Costs and tokens are tracked; daily and per-listing budgets apply.
4. **Research**: use the suggested research queries (links open eBay *sold* search), add comparables (manual, CSV,
   or a live provider if configured). The valuation recomputes automatically; correct the identification if the
   model is wrong.
5. **Decide**: the finance panel shows acquisition cost, fees for the chosen platform, net proceeds, profit, ROI,
   break-even and the maximum bid, with what-if controls (shipping, resale value, fees). Add to the watchlist with
   your own maximum bid and a reminder. Record feedback and, later, the purchase/sale outcome.

## Architecture

```
backend/outlier
  config.py            env settings + secrets (never persisted / returned)
  models.py            SQLAlchemy ORM (listings, snapshots, images, analysis runs, identifications, comps,
                       valuations, opportunities, watchlist, feedback, notes, outcomes, reference db, jobs, usage)
  ingestion/           csv/json, Personal Shopper e-mail (+IMAP), saved page HTML, comps import,
                       sgw_unofficial (off by default)
  services/listings.py normalization, dedupe (item id → URL → fingerprint), snapshots, image storage
  analysis/            schemas.py (validated structured outputs), prefilter (stage 1), prompts, images (resize/zoom),
                       guards.py (code-enforced jewelry/designer safeguard on model output), discrepancy detection,
                       reference matching, pipeline (tiered, cached, budgeted)
  providers/           VisionProvider interface; anthropic, gemini, demo adapters; registry; pricing; usage/budgets
  valuation/           engine.py (sold-only robust stats, scenarios, evidence grading); providers.py (eBay)
  finance/calc.py      deterministic acquisition/resale cost model, profit, ROI, break-even, max bid, sensitivity
  ranking/score.py     transparent weighted score + tiers (configurable heuristics)
  services/opportunity.py  valuation → finance → ranking recompute
  jobs/                durable DB-backed queue + worker thread (retries, resume on restart)
  api/                 FastAPI routers (~60 operations; OpenAPI at /docs)
  demo/                synthetic fixtures, seed reference entries
frontend/              Next.js app: dashboard, item analysis + research workspace, watchlist, analytics,
                       settings, import, reference
docs/                  research.md (integration research & legal notes), openapi.json, samples/, screenshots/
tools/                 capture bookmarklet
```

Stack choice: the recommended stack (FastAPI + SQLite/SQLAlchemy, Next.js) with an in-process job worker instead
of a separate queue service, because a single-user local app does not need Redis/Celery. Alembic is wired
(`backend/alembic`) for schema evolution and the PostgreSQL migration path (`OUTLIER_DATABASE_URL`).

## Integration status

| Component | Status | What it needs |
|---|---|---|
| Manual / CSV / JSON / saved-page / bookmarklet ingestion | Working | — |
| Personal Shopper e-mail parsing (.eml / HTML) | Working (parser tuned against synthetic mail; verify with a real e-mail) | — |
| IMAP polling of your mailbox | Implemented, untested against a live server | `OUTLIER_IMAP_HOST/USER/PASSWORD` |
| Claude vision analysis (triage + deep with zoom tool) | Implemented, tested with mocked SDK | `ANTHROPIC_API_KEY` |
| Gemini vision analysis | Implemented, tested with mocked SDK | `GEMINI_API_KEY` |
| Demo provider | Working (fixtures only) | — |
| Manual comparable sales | Working | — |
| eBay Marketplace Insights (sold data) | Interface implemented; limited-release API | eBay keyset **approved** for Marketplace Insights |
| eBay Browse (active listings, context only) | Interface implemented | any eBay keyset |
| Unofficial ShopGoodwill buyer API adapter | Implemented, **disabled by default**, unverified | read `docs/research.md`; `OUTLIER_ENABLE_UNOFFICIAL_SGW_API=true` only if authorized |
| n8n / automation webhooks (`/api/webhooks/listing`, `/api/webhooks/email`) | Working | `OUTLIER_WEBHOOK_TOKEN` |
| Autonomous bidding | Not implemented by design | — |

`GET /api/status` reports the live state of every component; the dashboard shows it.

## Key design points

- **Tiered, cost-controlled AI.** Rules → cheap vision triage → selective deep pass. Each model stage is cached on a
  hash of the images, seller text, schema version and model. `OUTLIER_DAILY_BUDGET_USD` and
  `OUTLIER_PER_LISTING_BUDGET_USD` are enforced before each call. Token usage, estimated cost, duration and errors
  are recorded per call and summarized in Analytics.
- **Structured, validated outputs** (`analysis/schemas.py`): observations vs candidates vs confirmed facts,
  confidence per candidate, evidence/counter-evidence, alternative explanations, missing information, research
  queries, value indicators, discrepancies. Jewelry materials are hypotheses with the verification needed; melt
  value is never computed. `analysis/guards.py` enforces this in code after every model call: 'confirmed'
  precious-metal/designer candidates are demoted to 'inferred', untested material confidence is capped at 0.7,
  any dollar melt value is removed and flagged, and overall confidence is capped at 0.95.
- **Discrepancy detection** combines the model's findings with deterministic checks (labels transcribed but not
  mentioned by the seller; "silver tone" vs a 925 mark; maker named by the model but not the seller) into a
  confidence-discounted *possible misidentification* signal that raises research priority but not value.
- **Reference-based discovery**: a growing reference database (makers, products, characteristics, identifiers,
  typical ranges, demand/liquidity) is matched by keywords and transcribed identifiers and fed to the deep prompt.
- **Finance**: `profit = net proceeds − (bid·(1+premium)·(1+tax) + shipping + handling + other)`; max bid is the
  tightest of the min-profit, min-ROI and capital-at-risk constraints, floored to the bid increment. Scenarios
  (conservative/expected/optimistic), a labelled risk-adjusted scenario, and a resale×shipping sensitivity grid.
- **Ranking**: weighted components (profit, risk-adjusted profit, ROI, identification confidence, evidence
  quality, sell likelihood, time to sell, competition, risk flags, misidentification signal) with time-remaining
  handling and feedback adjustments. Tiers: HIGH_CONFIDENCE, SPECULATIVE_HIGH_UPSIDE, NEEDS_RESEARCH, LOW_VALUE.
- **Learning loop**: feedback labels, identification corrections, valuation overrides and real purchase/sale
  outcomes are stored; ranking weights and feedback adjustments are configurable in Settings. No fine-tuning.

## Limitations (read these)

- The exact HTML of ShopGoodwill pages and Personal Shopper e-mails could not be verified from the build
  environment; both parsers are tolerant but may need small adjustments against a real sample.
- Live model calls were exercised only with mocked SDK responses (no credentials in the build environment).
- Sold-price data is manual unless eBay grants Marketplace Insights access. Reference "typical" ranges are
  guidance, not comps.
- Fee schedules in Settings are defaults as of 2026-10; verify them for your account/region.
- Docker: `docker compose up` builds both images, but the compose stack could not be run in the build environment
  (no Docker daemon); the native commands above are the verified path.
- The max bid shown on the dashboard carries a `?` marker when a cost (usually incoming shipping) is unknown;
  it was computed with that cost at $0 and the item page lists exactly which costs are missing.
- Scores and risk adjustments are heuristics until enough outcomes exist to calibrate them.

See `docs/research.md` for the integration research, legal notes and the review of `shopgoodwill-scripts`.
