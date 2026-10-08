# Technical research notes (2026-10)

Scope: what was investigated before building OUTLIER, what could be verified from the build environment, and what
could not. Items marked **unverified** could not be fetched from the sandbox (outbound HTTP to shopgoodwill.com,
ai.google.dev and developer.ebay.com was blocked by the environment's network policy) and should be re-checked.

## 1. ShopGoodwill search, notifications and permitted ingestion

| Mechanism | Status | Notes |
|---|---|---|
| Website search / Advanced Search | Manual | Normal browsing. OUTLIER ingests what you capture: saved page HTML, the capture bookmarklet, or manual entry. |
| **Personal Shopper** e-mail alerts | Permitted, implemented | ShopGoodwill sends e-mails when a listing matches a saved interest. OUTLIER parses `.eml` uploads / pasted HTML / IMAP polling of *your own* mailbox. The parser keys on `shopgoodwill.com/item/<id>` links and nearby price / bids / end time text. The exact e-mail markup is **unverified**; tune `backend/outlier/ingestion/email_import.py::_block_for_link` with a real sample. E-mail images are thumbnails, so upload full-size photos (or paste image URLs) before deep analysis. |
| Saved searches in the account | Manual | The site supports saved searches; they can trigger Personal Shopper e-mails. |
| Terms of Use | **Unverified text** | ShopGoodwill's terms (like most marketplaces) restrict robots / scrapers / automated access without permission. The sandbox could not fetch the page or `robots.txt`; read them yourself before enabling anything automated. OUTLIER's default configuration performs no automated access to shopgoodwill.com except fetching the photo URLs of listings *you* imported. |
| `buyerapi.shopgoodwill.com` (unofficial JSON API) | Implemented, **disabled by default** | Used by `scottmconway/shopgoodwill-scripts`. Not documented or sanctioned by ShopGoodwill; an unofficial endpoint is not permission. `OUTLIER_ENABLE_UNOFFICIAL_SGW_API=true` enables a read-only search + item-detail adapter with an honest User-Agent and a 5 s minimum interval, for authorized use only. Endpoint shapes copied from the reference project; **unverified** here. |
| Authorized higher-volume access | Open question | Contact ShopGoodwill (shopgoodwill.com → Contact) and ask for API / data-feed access for a buyer tool. Nothing in OUTLIER depends on getting it. |

## 2. scottmconway/shopgoodwill-scripts (GPL-3.0)

Cloned and read (HEAD 2025-08-11, 4 Python files, ~1,450 lines). Findings:

- `shopgoodwill.py` wraps `https://buyerapi.shopgoodwill.com/api`: `Search/ItemListing` (POST, paginated query JSON), `itemDetail/GetItemDetailModelByItemId/{id}`, `itemBid/ShowBidModal`, `itemDetail/CalculateShipping` (returns HTML containing `Shipping: <span id='shipping-span'>$x.xx`), plus authenticated favorites / saved searches / `ItemBid/PlaceBid`. Login uses a hard-coded AES key to "encrypt" credentials and spoofs a Firefox 12 User-Agent.
- `alert_on_new_query_results.py` runs saved query JSONs and logs new item IDs (Gotify notifications); `bid_sniper.py` places last-second bids from favorites notes; `schedule_bid.py` helper.
- Maintenance: active but small (single author; README notes 403s on quoted searches since 2025-03 and undocumented API quirks).
- Relevance: the query JSON shape and the item-detail field names informed `ingestion/sgw_unofficial.py`. **No code was copied**; the adapter is an independent implementation, so the GPL-3.0 license does not attach to OUTLIER. If you later vendor their code, OUTLIER (or at least that module/distribution) must comply with GPL-3.0.
- Deliberately **not** implemented: login, favorites automation, bid sniping, browser spoofing.

## 3. AI vision models and economics (prices as of 2026-10; editable in Settings → model pricing)

| Model | Input $/M | Output $/M | Role in OUTLIER |
|---|---|---|---|
| Claude Haiku 5.5 (`claude-haiku-5-5`) | 0.10 | 0.50 | Triage (alternative) |
| Gemini 2.5 Flash (`gemini-2.5-flash`) | 0.30 | 2.50 | Triage (default when `GEMINI_API_KEY` set) |
| Gemini 2.5 Flash-Lite | 0.10 | 0.40 | Optional cheaper triage |
| Claude Opus 5.5 (`claude-opus-5-5`) | 4.00 | 20.00 | Deep analysis (default) |
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | 2.00 | 10.00 | Cheaper deep alternative |
| Gemini 2.5 Pro | 1.25 | 10.00 | Deep alternative |

Image token costs: Claude ≈ (w×h)/750 tokens (a 1092 px image ≈ 1.6k tokens); Gemini ≈ 258 tokens per 768 px tile.
A typical triage call with 6 downscaled photos costs well under $0.01; a deep Opus call with zoom crops is usually
$0.05–0.20. The pipeline caches by image/text hash, has per-day and per-listing budgets, and never sends unchanged
inputs twice. Gemini pricing figures are from third-party summaries (**unverified** against ai.google.dev).

## 4. Sold-listing data providers

| Source | Access | OUTLIER status |
|---|---|---|
| Manual / CSV / JSON comps with URL, date, price | — | Working (the backbone) |
| eBay **Marketplace Insights API** (`/buy/marketplace_insights/v1_beta/item_sales/search`, 90-day sold history) | Limited release; requires an approved keyset | Interface implemented (`valuation/providers.py`); activates with `EBAY_CLIENT_ID/SECRET` *and* eBay approval. Unapproved keysets get 401/403, surfaced as a clear error. |
| eBay **Browse API** (active listings) | Any eBay developer keyset (client-credentials) | Implemented; results are stored as `comp_type=active` and never used in valuations. |
| eBay Finding API `findCompletedItems` | Decommissioned | Not used. |
| Terapeak (eBay Seller Hub product research) | Web UI only, no API | Manual: copy sold results into the comps CSV. |
| WorthPoint | Subscription, no public API | Manual entry. |
| eBay sold search in the browser (`LH_Sold=1&LH_Complete=1`) | Manual; eBay has increasingly required sign-in for sold filters | The research panel links each AI research query to this search; you paste what you find. |

## 5. Specialized jewelry research (manual workflow)

Hallmark / maker lookups: 925-1000.com (silver marks), Lang Antiques encyclopedia, Mexican silver registry references
(eagle marks, TC-/TS- codes), Native American hallmark references, auction-house archives (Rago, Wright, Heritage) for
studio jewelry, and Etsy/eBay sold searches by maker. The reference database (`/reference`) is seeded with ~25
makers/characteristics and is meant to grow with your own notes and price evidence.

## 6. Local macOS (Apple Silicon) setup

Python 3.11+ via `uv`, Node 20/22 via Homebrew or nvm, SQLite (bundled). No Docker required; `docker compose up`
works too. All model calls go to hosted APIs; nothing runs locally on the GPU.
