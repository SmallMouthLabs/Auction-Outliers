"use client";
import { ExternalLink, Plus, RefreshCw, Search, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { fmtDate, money, num, relTime } from "@/lib/format";
import type { CompIn, Comparable, ListingDetail, SoldDataProvider } from "@/lib/types";
import { Badge, DemoBadge, EvidenceBadge } from "@/components/ui/badges";
import { Alert, ApiErrorAlert, Card, Field, KV, Spinner, Stat } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

const COMP_TYPES = ["exact", "same_maker", "category", "active"];
const QUALITIES = ["high", "medium", "low"];

export function ComparablesPanel({ listing, onUpdate, providers }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void; providers: SoldDataProvider[] }) {
  const sold = listing.comparables.filter((c) => c.is_sold && c.comp_type !== "active");
  const active = listing.comparables.filter((c) => !c.is_sold || c.comp_type === "active");
  const used = new Set(listing.valuation_full?.detail?.used_comp_ids ?? []);
  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_360px]">
      <div className="flex flex-col gap-3">
        <CompTable title={`Sold comparables (${sold.length})`} comps={sold} listing={listing} onUpdate={onUpdate} used={used} />
        <CompTable title={`Active listings (${active.length})`} subtitle="asking prices, not used in valuation" comps={active} listing={listing} onUpdate={onUpdate} used={used} />
        <div className="grid gap-3 lg:grid-cols-2">
          <AddCompForm listing={listing} onUpdate={onUpdate} />
          <div className="flex flex-col gap-3">
            <ImportComps listing={listing} onUpdate={onUpdate} />
            <SearchComps listing={listing} onUpdate={onUpdate} providers={providers} />
          </div>
        </div>
      </div>
      <ValuationPanel listing={listing} onUpdate={onUpdate} />
    </div>
  );
}

async function reload(id: number, onUpdate: (d: ListingDetail) => void) {
  onUpdate(await api.listing(id));
}

function CompTable({ title, subtitle, comps, listing, onUpdate, used }: { title: string; subtitle?: string; comps: Comparable[]; listing: ListingDetail; onUpdate: (d: ListingDetail) => void; used: Set<number> }) {
  const toast = useToast();
  const [busy, setBusy] = useState<number | null>(null);
  async function patch(c: Comparable, body: Parameters<typeof api.patchComp>[2]) {
    setBusy(c.id);
    try { await api.patchComp(listing.id, c.id, body); await reload(listing.id, onUpdate); toast.success("Comparable updated", listing.valuation?.method === "user_override" ? "Saved. A user override is active; click Recalculate to use comparables." : "Valuation recalculated."); }
    catch (e) { toast.apiError(e, "Update comparable"); } finally { setBusy(null); }
  }
  async function del(c: Comparable) {
    if (!confirm(`Delete comparable "${c.title}"?`)) return;
    setBusy(c.id);
    try { await api.deleteComp(listing.id, c.id); await reload(listing.id, onUpdate); toast.info("Comparable deleted"); }
    catch (e) { toast.apiError(e, "Delete comparable"); } finally { setBusy(null); }
  }
  return (
    <Card title={<span>{title}{subtitle && <span className="ml-2 normal-case tracking-normal text-amber">· {subtitle}</span>}</span>} bodyClass="p-0">
      {comps.length === 0 ? <p className="p-3 text-xs text-dim">None.</p> : (
        <div className="scrollbar-thin overflow-x-auto">
          <table className="tbl min-w-[720px]">
            <thead><tr><th>Title</th><th>Market</th><th>Date</th><th className="r">Price</th><th>Type</th><th className="r">Sim.</th><th>Evidence</th><th>Notes</th><th></th></tr></thead>
            <tbody>
              {comps.map((c) => (
                <tr key={c.id} className={used.has(c.id) ? "" : "opacity-80"}>
                  <td className="max-w-[260px]">
                    <div className="flex items-center gap-1">
                      {c.url ? <a href={c.url} target="_blank" rel="noopener noreferrer" className="truncate hover:underline" title={c.title}>{c.title}</a> : <span className="truncate" title={c.title}>{c.title}</span>}
                      {c.url && <ExternalLink size={10} className="shrink-0 text-dim" />}
                    </div>
                    <div className="flex gap-1 text-[10px] text-dim">
                      {used.has(c.id) && <Badge tone="green">used</Badge>}
                      {c.is_demo && <DemoBadge />}
                      {c.accepted_offer && <Badge tone="blue">best offer</Badge>}
                      <span>{c.source}</span>
                    </div>
                  </td>
                  <td className="text-xs">{c.marketplace}</td>
                  <td className="num whitespace-nowrap text-xs" title={fmtDate(c.sold_date)}>{c.sold_date ? relTime(c.sold_date) : <span className="text-dim">asking</span>}</td>
                  <td className="r num whitespace-nowrap">{money(c.price)}{c.shipping_included ? <div className="text-[10px] text-dim">incl. ship</div> : c.shipping_amount != null ? <div className="text-[10px] text-dim">+{money(c.shipping_amount)} ship</div> : null}</td>
                  <td>
                    <select className="input btn-xs w-auto py-0.5" value={c.comp_type} disabled={busy === c.id} onChange={(e) => patch(c, { comp_type: e.target.value })} aria-label="Comp type">
                      {COMP_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td className="r">
                    <input className="input num w-16 py-0.5 text-right" type="number" min="0" max="1" step="0.05" defaultValue={c.similarity ?? 0} disabled={busy === c.id} aria-label="Similarity"
                      onBlur={(e) => { const v = Number(e.target.value); if (Number.isFinite(v) && v !== c.similarity) patch(c, { similarity: Math.max(0, Math.min(1, v)) }); }} />
                  </td>
                  <td>
                    <select className="input btn-xs w-auto py-0.5" value={c.evidence_quality} disabled={busy === c.id} onChange={(e) => patch(c, { evidence_quality: e.target.value })} aria-label="Evidence quality">
                      {QUALITIES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td className="max-w-[160px] text-xs text-muted"><div className="truncate" title={[c.condition, c.differences].filter(Boolean).join(" · ")}>{[c.condition, c.differences].filter(Boolean).join(" · ") || "—"}</div></td>
                  <td><button className="btn btn-xs btn-danger" onClick={() => del(c)} disabled={busy === c.id} aria-label="Delete comparable">{busy === c.id ? <Spinner size={11} /> : <Trash2 size={11} />}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function AddCompForm({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const blank = { title: "", marketplace: "ebay", url: "", sold_date: "", price: "", shipping_included: false, shipping_amount: "", is_sold: true, accepted_offer: false, comp_type: "same_maker", similarity: "0.7", evidence_quality: "medium", condition: "", differences: "" };
  const [f, setF] = useState(blank);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: CompIn = {
      title: f.title.trim(), marketplace: f.marketplace || "ebay", url: f.url || null, sold_date: f.sold_date ? new Date(f.sold_date).toISOString() : null,
      price: f.price === "" ? null : Number(f.price), shipping_included: f.shipping_included, shipping_amount: f.shipping_amount === "" ? null : Number(f.shipping_amount),
      is_sold: f.is_sold, accepted_offer: f.accepted_offer, comp_type: f.is_sold ? f.comp_type : "active", similarity: Number(f.similarity), evidence_quality: f.evidence_quality,
      condition: f.condition || null, differences: f.differences || null, source: "manual",
    };
    setBusy(true);
    try { await api.addComp(listing.id, body); await reload(listing.id, onUpdate); toast.success("Comparable added", listing.valuation?.method === "user_override" ? "Saved. A user override is active; click Recalculate to use comparables." : "Valuation recalculated."); setF(blank); }
    catch (err) { toast.apiError(err, "Add comparable"); } finally { setBusy(false); }
  }
  return (
    <Card title="Add comparable">
      <form onSubmit={submit} className="grid grid-cols-2 gap-2">
        <Field label="Title" className="col-span-2"><input className="input" required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Sold listing title" /></Field>
        <Field label="Marketplace"><input className="input" value={f.marketplace} onChange={(e) => setF({ ...f, marketplace: e.target.value })} /></Field>
        <Field label="URL"><input className="input" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} placeholder="https://" /></Field>
        <Field label="Price"><input className="input" type="number" step="0.01" min="0" required value={f.price} onChange={(e) => setF({ ...f, price: e.target.value })} /></Field>
        <Field label="Sold date"><input className="input" type="date" value={f.sold_date} onChange={(e) => setF({ ...f, sold_date: e.target.value })} disabled={!f.is_sold} /></Field>
        <Field label="Shipping amount"><input className="input" type="number" step="0.01" min="0" value={f.shipping_amount} onChange={(e) => setF({ ...f, shipping_amount: e.target.value })} /></Field>
        <div className="flex flex-col justify-end gap-1 pb-1 text-xs">
          <label className="flex items-center gap-1.5"><input type="checkbox" checked={f.is_sold} onChange={(e) => setF({ ...f, is_sold: e.target.checked })} /> Sold (vs. active asking)</label>
          <label className="flex items-center gap-1.5"><input type="checkbox" checked={f.shipping_included} onChange={(e) => setF({ ...f, shipping_included: e.target.checked })} /> Shipping included</label>
          <label className="flex items-center gap-1.5"><input type="checkbox" checked={f.accepted_offer} onChange={(e) => setF({ ...f, accepted_offer: e.target.checked })} /> Best offer accepted</label>
        </div>
        <Field label="Type"><select className="input" value={f.comp_type} onChange={(e) => setF({ ...f, comp_type: e.target.value })} disabled={!f.is_sold}>{COMP_TYPES.filter((t) => t !== "active").map((t) => <option key={t} value={t}>{t}</option>)}</select></Field>
        <Field label="Similarity (0-1)"><input className="input" type="number" min="0" max="1" step="0.05" value={f.similarity} onChange={(e) => setF({ ...f, similarity: e.target.value })} /></Field>
        <Field label="Evidence quality"><select className="input" value={f.evidence_quality} onChange={(e) => setF({ ...f, evidence_quality: e.target.value })}>{QUALITIES.map((t) => <option key={t} value={t}>{t}</option>)}</select></Field>
        <Field label="Condition"><input className="input" value={f.condition} onChange={(e) => setF({ ...f, condition: e.target.value })} /></Field>
        <Field label="Differences vs. this item" className="col-span-2"><input className="input" value={f.differences} onChange={(e) => setF({ ...f, differences: e.target.value })} /></Field>
        <div className="col-span-2 flex justify-end"><button className="btn btn-sm btn-primary" disabled={busy}>{busy ? <Spinner /> : <Plus size={13} />} Add comp</button></div>
      </form>
    </Card>
  );
}

function ImportComps({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<unknown>(null);
  async function onFile(files: FileList | null) {
    if (!files?.[0]) return;
    setBusy(true);
    try {
      const r = await api.importComps(listing.id, files[0]);
      setResult(r);
      await reload(listing.id, onUpdate);
      toast.success("Comparables imported", typeof r === "object" && r && "added" in r ? `${(r as { added: number }).added} added` : undefined);
    } catch (e) { toast.apiError(e, "Import comparables"); } finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  }
  return (
    <Card title="Import comps (CSV / JSON)">
      <input ref={ref} type="file" accept=".csv,.json,text/csv,application/json" className="hidden" onChange={(e) => onFile(e.target.files)} />
      <div className="flex items-center gap-2">
        <button className="btn btn-sm" onClick={() => ref.current?.click()} disabled={busy}>{busy ? <Spinner /> : <Upload size={13} />} Choose file</button>
        <span className="text-[11px] text-dim">Columns: title, price, sold_date, url, marketplace, comp_type, similarity, evidence_quality, is_sold…</span>
      </div>
      {result !== null && <pre className="scrollbar-thin mt-2 max-h-32 overflow-auto rounded bg-elev-2 p-2 text-[11px] text-muted">{JSON.stringify(result, null, 1)}</pre>}
    </Card>
  );
}

function SearchComps({ listing, onUpdate, providers }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void; providers: SoldDataProvider[] }) {
  const toast = useToast();
  const [query, setQuery] = useState(listing.identification?.summary ?? listing.title);
  const [provider, setProvider] = useState(providers.find((p) => p.name !== "manual_entry")?.name ?? "ebay_marketplace_insights");
  const [save, setSave] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [results, setResults] = useState<CompIn[] | null>(null);
  const live = providers.filter((p) => p.name !== "manual_entry");
  async function run(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setResults(null);
    try {
      const r = await api.searchComps(listing.id, { query, provider, save, limit: 20 });
      setResults(r.results);
      if (r.saved) { await reload(listing.id, onUpdate); toast.success(`Saved ${r.results.length} comps from ${provider}`); }
    } catch (err) { setError(err instanceof ApiError ? err : new ApiError(0, (err as Error).message)); } finally { setBusy(false); }
  }
  return (
    <Card title="Search sold-data provider">
      <form onSubmit={run} className="flex flex-col gap-2">
        <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="search query" />
        <div className="flex flex-wrap items-center gap-2">
          <select className="input w-auto" value={provider} onChange={(e) => setProvider(e.target.value)}>
            {live.map((p) => <option key={p.name} value={p.name}>{p.name}{p.available ? "" : " (not configured)"}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} /> Save results as comps</label>
          <button className="btn btn-sm ml-auto" disabled={busy || !query.trim()}>{busy ? <Spinner /> : <Search size={13} />} Search</button>
        </div>
      </form>
      {live.length > 0 && !live.find((p) => p.name === provider)?.available && (
        <p className="mt-1.5 text-[11px] text-dim">{live.find((p) => p.name === provider)?.note}</p>
      )}
      {error && <ApiErrorAlert error={error} className="mt-2" />}
      {results && (
        results.length === 0 ? <Alert kind="info" className="mt-2">No results.</Alert> : (
          <ul className="mt-2 max-h-48 space-y-1 overflow-auto text-xs">{results.map((r, i) => <li key={i} className="flex justify-between gap-2"><span className="truncate">{r.title}</span><span className="num shrink-0">{money(r.price)}</span></li>)}</ul>
        )
      )}
    </Card>
  );
}

function ValuationPanel({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const v = listing.valuation_full;
  const det = v?.detail;
  const [busy, setBusy] = useState<string | null>(null);
  const [f, setF] = useState({ expected: v?.expected?.toString() ?? "", conservative: v?.conservative?.toString() ?? "", optimistic: v?.optimistic?.toString() ?? "", note: "" });
  const isOverride = v?.method === "user_override" || v?.method === "override" || (v?.method ?? "").includes("override");
  const alc = det?.active_listing_context && "n" in det.active_listing_context ? det.active_listing_context : null;
  const excluded = (det?.excluded ?? []) as unknown[];

  async function override(e: React.FormEvent) {
    e.preventDefault();
    const exp = Number(f.expected);
    if (!(exp > 0)) { toast.error("Expected value must be > 0"); return; }
    setBusy("override");
    try {
      const d = await api.overrideValuation(listing.id, { expected: exp, conservative: f.conservative === "" ? null : Number(f.conservative), optimistic: f.optimistic === "" ? null : Number(f.optimistic), note: f.note });
      onUpdate(d); toast.success("Valuation overridden", "Finance and score recomputed.");
    } catch (err) { toast.apiError(err, "Override valuation"); } finally { setBusy(null); }
  }
  async function recalc() {
    setBusy("recalc");
    try { const d = await api.recalcValuation(listing.id); onUpdate(d); toast.success("Valuation recalculated from comparables"); }
    catch (err) { toast.apiError(err, "Recalculate valuation"); } finally { setBusy(null); }
  }

  return (
    <div className="flex flex-col gap-3">
      <Card title="Valuation" actions={<button className="btn btn-xs" onClick={recalc} disabled={busy !== null} title="Clear override and recompute from comps">{busy === "recalc" ? <Spinner size={11} /> : <RefreshCw size={11} />} Recalculate</button>}>
        {!v ? <p className="text-xs text-dim">No valuation. Add sold comparables or set an override.</p> : (
          <>
            <div className="mb-2 flex flex-wrap items-center gap-1.5">
              <Badge tone={isOverride ? "accent" : "gray"}>{v.method}</Badge>
              <EvidenceBadge quality={v.evidence_quality} speculative={v.is_speculative} />
              <span className="num text-xs text-dim">{v.n_sold_comps} sold comp{v.n_sold_comps === 1 ? "" : "s"}</span>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              <Stat label="Conservative" value={money(v.conservative, { cents: false })} />
              <Stat label="Expected" value={money(v.expected, { cents: false })} tone="blue" />
              <Stat label="Optimistic" value={money(v.optimistic, { cents: false })} />
            </div>
            {(det?.notes?.length ?? 0) > 0 && (
              <ul className="mt-2 space-y-0.5 text-xs text-amber">{det!.notes!.map((n, i) => <li key={i}>• {n}</li>)}</ul>
            )}
            {det?.note && <p className="mt-2 text-xs text-muted">{String(det.note)}</p>}
            {det?.stats && (
              <div className="mt-2">
                <div className="label">Stats</div>
                <KV rows={Object.entries(det.stats).map(([k, val]) => [k.replace(/_/g, " "), <span key={k} className="num">{typeof val === "number" ? num(val, 2) : String(val ?? "—")}</span>])} className="text-xs" />
              </div>
            )}
            {alc && alc.n ? (
              <div className="mt-2 rounded border border-amber/30 bg-amber/5 p-2 text-xs">
                <div className="font-medium">Active listings context ({alc.n})</div>
                <div className="num text-muted">asking {money(alc.min_asking, { cents: false })} · median {money(alc.median_asking, { cents: false })} · max {money(alc.max_asking, { cents: false })}</div>
                <div className="text-dim">{alc.note || "Asking prices only. Not used in the valuation."}</div>
              </div>
            ) : null}
            {excluded.length > 0 && (
              <div className="mt-2 text-xs">
                <div className="label">Excluded comps</div>
                <ul className="space-y-0.5 text-muted">{excluded.map((x, i) => <li key={i}>{typeof x === "object" && x ? `#${(x as { comp_id?: number; id?: number }).comp_id ?? (x as { id?: number }).id ?? "?"}: ${(x as { reason?: string }).reason ?? JSON.stringify(x)}` : `#${String(x)}`}</li>)}</ul>
              </div>
            )}
            <div className="mt-2 text-[11px] text-dim">Computed {relTime(v.created_at)}</div>
          </>
        )}
      </Card>
      <Card title="Override valuation">
        <form onSubmit={override} className="grid grid-cols-3 gap-2">
          <Field label="Conservative"><input className="input" type="number" step="1" min="0" value={f.conservative} onChange={(e) => setF({ ...f, conservative: e.target.value })} /></Field>
          <Field label="Expected *"><input className="input" type="number" step="1" min="0.01" required value={f.expected} onChange={(e) => setF({ ...f, expected: e.target.value })} /></Field>
          <Field label="Optimistic"><input className="input" type="number" step="1" min="0" value={f.optimistic} onChange={(e) => setF({ ...f, optimistic: e.target.value })} /></Field>
          <Field label="Note (why)" className="col-span-3"><input className="input" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} placeholder="e.g. I know this maker sells for more at auction" /></Field>
          <div className="col-span-3 flex justify-end"><button className="btn btn-sm btn-primary" disabled={busy !== null}>{busy === "override" ? <Spinner /> : null} Apply override</button></div>
        </form>
      </Card>
    </div>
  );
}
