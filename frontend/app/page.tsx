"use client";
import { Database, FlaskConical, RefreshCw, Search, Upload, X } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { ListingSummary } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { ListingTable, type SortKey } from "@/components/listings/listing-table";
import { ApiErrorAlert, EmptyState, Skeleton, Toggle } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

const TIERS = [
  ["", "All tiers"], ["HIGH_CONFIDENCE", "High confidence"], ["SPECULATIVE_HIGH_UPSIDE", "Speculative upside"], ["NEEDS_RESEARCH", "Needs research"], ["LOW_VALUE", "Low value"],
];
const SORTS: [SortKey, string][] = [
  ["score", "Opportunity score"], ["profit", "Expected profit"], ["max_bid", "Max bid"], ["ends_at", "Ending soonest"], ["current_bid", "Current bid"], ["confidence", "Confidence"], ["updated", "Recently updated"],
];

export default function DashboardPage() {
  return (
    <Suspense fallback={<Skeleton className="h-40" />}>
      <Dashboard />
    </Suspense>
  );
}

function Dashboard() {
  const sp = useSearchParams();
  const router = useRouter();
  const toast = useToast();

  // URL-backed filter state so views are shareable / back-button friendly
  const q = sp.get("q") ?? "";
  const domain = sp.get("domain") ?? "";
  const tier = sp.get("tier") ?? "";
  const source = sp.get("source") ?? "";
  const status = sp.get("status") ?? "";
  const includeDemo = (sp.get("include_demo") ?? "1") !== "0";
  const includeArchived = sp.get("include_archived") === "1";
  const watchOnly = sp.get("watchlist_only") === "1";
  const sort = (sp.get("sort") as SortKey) || "score";
  const order = (sp.get("order") as "asc" | "desc") || (sort === "ends_at" ? "asc" : "desc");
  const [qInput, setQInput] = useState(q);
  useEffect(() => setQInput(q), [q]);

  const setParams = useCallback((patch: Record<string, string | null>) => {
    const p = new URLSearchParams(sp.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v === null || v === "") p.delete(k); else p.set(k, v);
    }
    router.replace(`/?${p.toString()}`, { scroll: false });
  }, [router, sp]);

  const listings = useApi(
    () => api.listings({ q, domain, tier, source, status, include_demo: includeDemo, include_archived: includeArchived, watchlist_only: watchOnly, sort, order, limit: 200 }),
    [q, domain, tier, source, status, includeDemo, includeArchived, watchOnly, sort, order],
    { pollMs: 60000 },
  );

  const onSort = (s: SortKey) => {
    if (s === sort) setParams({ order: order === "desc" ? "asc" : "desc" });
    else setParams({ sort: s, order: s === "ends_at" ? "asc" : "desc" });
  };

  const onChanged = (u: ListingSummary) => listings.setData((prev) => prev ? { ...prev, items: prev.items.map((x) => x.id === u.id ? u : x) } : prev);

  const [demoBusy, setDemoBusy] = useState(false);
  async function runDemo() {
    setDemoBusy(true);
    try {
      const r = await api.demoRun();
      toast.success("Demo data loaded", `${r.loaded.listings.length} synthetic listings analyzed with the demo provider.`);
      await listings.refresh();
    } catch (e) { toast.apiError(e, "Demo run"); } finally { setDemoBusy(false); }
  }

  const sources = useMemo(() => Array.from(new Set((listings.data?.items ?? []).map((l) => l.source))).sort(), [listings.data]);
  const anyFilter = q || domain || tier || source || status || !includeDemo || includeArchived || watchOnly;
  const items = listings.data?.items ?? [];
  const counts = useMemo(() => {
    const c = { HIGH_CONFIDENCE: 0, SPECULATIVE_HIGH_UPSIDE: 0, NEEDS_RESEARCH: 0, LOW_VALUE: 0, overMax: 0 };
    for (const l of items) {
      const t = l.opportunity?.tier; if (t && t in c) c[t as keyof typeof c]++;
      if (l.opportunity?.finance?.over_max_bid) c.overMax++;
    }
    return c;
  }, [items]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Opportunity dashboard</h1>
          <p className="text-xs text-muted">
            {listings.data ? <>{listings.data.total} listing{listings.data.total === 1 ? "" : "s"} · <span className="text-green">{counts.HIGH_CONFIDENCE} high confidence</span> · <span className="text-amber">{counts.SPECULATIVE_HIGH_UPSIDE} speculative</span> · <span className="text-blue">{counts.NEEDS_RESEARCH} needs research</span> · {counts.LOW_VALUE} low value{counts.overMax ? <> · <span className="text-red">{counts.overMax} over max bid</span></> : null}</> : "Loading…"}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <button className="btn btn-sm" onClick={() => listings.refresh()} title="Refresh"><RefreshCw size={13} className={listings.refreshing ? "animate-spin" : ""} /> Refresh</button>
          <Link href="/import" className="btn btn-sm btn-primary"><Upload size={13} /> Import</Link>
        </div>
      </div>

      <form
        className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-elev px-3 py-2"
        onSubmit={(e) => { e.preventDefault(); setParams({ q: qInput }); }}
      >
        <div className="relative min-w-[220px] flex-1">
          <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-dim" />
          <input className="input pl-7" placeholder="Search title, description, category…" value={qInput} onChange={(e) => setQInput(e.target.value)} aria-label="Search" />
          {qInput && <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-dim hover:text-fg" onClick={() => { setQInput(""); setParams({ q: null }); }} aria-label="Clear search"><X size={13} /></button>}
        </div>
        <select className="input w-auto" value={domain} onChange={(e) => setParams({ domain: e.target.value })} aria-label="Domain">
          <option value="">All domains</option><option value="clothing">Clothing</option><option value="jewelry">Jewelry</option><option value="other">Other</option><option value="unknown">Unknown</option>
        </select>
        <select className="input w-auto" value={tier} onChange={(e) => setParams({ tier: e.target.value })} aria-label="Tier">
          {TIERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className="input w-auto" value={source} onChange={(e) => setParams({ source: e.target.value })} aria-label="Source">
          <option value="">All sources</option>
          {sources.map((s) => <option key={s} value={s}>{s}</option>)}
          {source && !sources.includes(source) && <option value={source}>{source}</option>}
        </select>
        <select className="input w-auto" value={status} onChange={(e) => setParams({ status: e.target.value })} aria-label="Status">
          <option value="">Any status</option><option value="active">Active</option><option value="ended">Ended</option>
        </select>
        <select className="input w-auto" value={sort} onChange={(e) => setParams({ sort: e.target.value, order: e.target.value === "ends_at" ? "asc" : "desc" })} aria-label="Sort by">
          {SORTS.map(([v, l]) => <option key={v} value={v}>Sort: {l}</option>)}
        </select>
        <button type="button" className="btn btn-sm" onClick={() => setParams({ order: order === "desc" ? "asc" : "desc" })} title="Toggle sort order">{order === "desc" ? "Desc" : "Asc"}</button>
        <Toggle checked={includeDemo} onChange={(v) => setParams({ include_demo: v ? null : "0" })} label={<span className="flex items-center gap-1"><FlaskConical size={12} className="text-demo" />Demo</span>} />
        <Toggle checked={watchOnly} onChange={(v) => setParams({ watchlist_only: v ? "1" : null })} label="Watchlist only" />
        <Toggle checked={includeArchived} onChange={(v) => setParams({ include_archived: v ? "1" : null })} label="Archived" />
        {anyFilter && <button type="button" className="btn btn-sm btn-ghost text-muted" onClick={() => router.replace("/")}>Clear</button>}
        <button type="submit" className="hidden">Search</button>
      </form>

      {listings.error && <ApiErrorAlert error={listings.error} />}

      {listings.loading && !listings.data ? (
        <div className="flex flex-col gap-1.5">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-14" />)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={<Database size={28} />} title={anyFilter ? "No listings match these filters" : "No listings yet"}>
          {anyFilter ? (
            <p>Try clearing filters, or <Link href="/import" className="text-accent underline">import</Link> new auctions.</p>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <p>Import auctions manually, via CSV, a ShopGoodwill Personal Shopper e-mail (.eml) or a saved item page, then run analysis. Or load the synthetic demo set to explore the workflow end-to-end without API keys.</p>
              <div className="flex gap-2">
                <button className="btn btn-primary btn-sm" onClick={runDemo} disabled={demoBusy}><FlaskConical size={13} /> {demoBusy ? "Loading demo…" : "Load demo data"}</button>
                <Link href="/import" className="btn btn-sm"><Upload size={13} /> Import listings</Link>
              </div>
            </div>
          )}
        </EmptyState>
      ) : (
        <ListingTable items={items} sort={sort} order={order} onSort={onSort} onChanged={onChanged} />
      )}
      {listings.data && listings.data.total > items.length && (
        <p className="text-xs text-dim">Showing first {items.length} of {listings.data.total}. Narrow the filters to see the rest.</p>
      )}
    </div>
  );
}
