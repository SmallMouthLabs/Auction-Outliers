"use client";
import { AlertTriangle, Bot, ChevronDown, ChevronRight, ExternalLink, Image as ImageIcon, Play, RotateCcw, Search, Undo2 } from "lucide-react";
import { useState } from "react";
import { ApiError, api, ebaySoldSearchUrl } from "@/lib/api";
import { conf, fmtDate, money, num, relTime, titleCase } from "@/lib/format";
import type { AnalysisRun, AnalyzeIn, AnalyzeStageSummary, IdentificationCorrection, IdentificationFull, ListingDetail } from "@/lib/types";
import { Badge, ConfidenceBar, DemoBadge, OriginBadge, StatusBadge, StrengthBadge } from "@/components/ui/badges";
import { Alert, ApiErrorAlert, Card, CopyButton, EmptyState, Field, KV, Pre, Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

function ImgRef({ index, onFocusImage }: { index: number | null | undefined; onFocusImage: (i: number) => void }) {
  if (index === null || index === undefined) return null;
  return (
    <button type="button" onClick={() => onFocusImage(index)} className="inline-flex items-center gap-0.5 rounded border border-border bg-elev-2 px-1 text-[10px] text-muted hover:border-accent hover:text-fg" title={`Show photo #${index}`}>
      <ImageIcon size={9} /> #{index}
    </button>
  );
}

function List({ items, empty = "none" }: { items: (string | null | undefined)[] | undefined; empty?: string }) {
  const xs = (items || []).filter(Boolean) as string[];
  if (!xs.length) return <span className="text-dim">{empty}</span>;
  return <ul className="list-disc space-y-0.5 pl-4">{xs.map((x, i) => <li key={i}>{x}</li>)}</ul>;
}

function Section({ title, children, count, defaultOpen = true }: { title: string; children: React.ReactNode; count?: number; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-border last:border-b-0">
      <button className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted hover:text-fg" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {title}
        {count !== undefined && <span className="num rounded bg-elev-2 px-1 text-[10px]">{count}</span>}
      </button>
      {open && <div className="px-3 pb-3 text-sm">{children}</div>}
    </div>
  );
}

export function Identification({ listing, onUpdate, onFocusImage }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void; onFocusImage: (i: number) => void }) {
  const ident = listing.identification_full;
  const d = ident?.data ?? {};
  const disc = ident?.discrepancy && "findings" in ident.discrepancy ? ident.discrepancy : null;
  const clothing = d.clothing;
  const jewelry = d.jewelry;

  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_380px]">
      <div className="flex flex-col gap-3">
        {!ident ? (
          <EmptyState icon={<Bot size={26} />} title="No identification yet">Run triage or deep analysis (right), or enter a manual identification below.</EmptyState>
        ) : (
          <Card bodyClass="p-0">
            <div className="border-b border-border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <OriginBadge origin={ident.origin} />
                {ident.is_demo && ident.origin !== "demo" && <DemoBadge />}
                <Badge tone="gray">{ident.domain || "unknown"}</Badge>
                {ident.warrants_research && <Badge tone="blue"><Search size={10} /> Warrants research</Badge>}
                {d.demand_indicator && <Badge tone={d.demand_indicator === "high" ? "green" : d.demand_indicator === "low" ? "red" : "amber"}>demand {d.demand_indicator}</Badge>}
                {d.liquidity_indicator && <Badge tone={d.liquidity_indicator === "high" ? "green" : d.liquidity_indicator === "low" ? "red" : "amber"}>liquidity {d.liquidity_indicator}</Badge>}
                <span className="ml-auto text-[11px] text-dim" title={fmtDate(ident.created_at)}>{d._meta?.provider ? `${d._meta.provider} · ${d._meta.model}` : ""} {relTime(ident.created_at)}</span>
              </div>
              <h2 className="mt-2 text-base font-semibold leading-snug">{ident.summary}</h2>
              <div className="mt-1.5 flex items-center gap-3 text-xs text-muted">
                <span>Confidence</span><ConfidenceBar value={ident.confidence} />
                {d.research_rationale && <span className="text-dim">· {d.research_rationale}</span>}
              </div>
              {d.user_correction && (
                <div className="mt-2 rounded border border-accent/30 bg-accent/5 p-2 text-xs">
                  <strong>Your correction</strong>: {[d.user_correction.brand_or_maker && `maker: ${d.user_correction.brand_or_maker}`, d.user_correction.era && `era: ${d.user_correction.era}`, d.user_correction.notes].filter(Boolean).join(" · ") || "no extra details"}
                </div>
              )}
              {(d.risk_flags?.length ?? 0) > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">{d.risk_flags!.map((r, i) => <Badge key={i} tone="red"><AlertTriangle size={10} /> {r}</Badge>)}</div>
              )}
            </div>

            {disc && disc.findings?.length > 0 && (
              <Section title="Discrepancies: seller claim vs visual evidence" count={disc.findings.length}>
                <div className="mb-1.5 flex items-center gap-2 text-xs text-muted">
                  <span>Misidentification signal</span>
                  <span className={`num font-semibold ${(disc.signal ?? 0) >= 0.6 ? "text-red" : (disc.signal ?? 0) >= 0.3 ? "text-amber" : "text-muted"}`}>{disc.signal != null ? (disc.signal * 100).toFixed(0) : "—"}</span>
                  {disc.raw_signal != null && <span className="text-dim">(raw {(disc.raw_signal * 100).toFixed(0)})</span>}
                  {disc.note && <span className="text-dim">· {disc.note}</span>}
                </div>
                <table className="tbl">
                  <thead><tr><th>Seller claims</th><th>Visual evidence</th><th>Strength</th><th>Src</th></tr></thead>
                  <tbody>
                    {disc.findings.map((f, i) => (
                      <tr key={i}>
                        <td className="text-muted">{f.seller_claim}</td>
                        <td>{f.visual_evidence} <ImgRef index={f.image_index} onFocusImage={onFocusImage} /></td>
                        <td><StrengthBadge strength={f.strength} /></td>
                        <td className="text-dim">{f.source || "model"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Section>
            )}

            <Section title="Candidates" count={d.candidates?.length}>
              {!d.candidates?.length ? <span className="text-dim">none</span> : (
                <div className="flex flex-col gap-2">
                  {d.candidates.map((c, i) => (
                    <div key={i} className={`rounded-md border p-2 ${i === 0 ? "border-accent/40 bg-accent/5" : "border-border"}`}>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{c.label}</span>
                        {c.brand_or_maker && <Badge tone="purple">{c.brand_or_maker}</Badge>}
                        {c.status && <Badge tone={c.status === "observed" ? "green" : c.status === "inferred" ? "amber" : "gray"}>{c.status}</Badge>}
                        <span className="ml-auto"><ConfidenceBar value={c.confidence} /></span>
                      </div>
                      <div className="mt-1.5 grid gap-2 text-xs sm:grid-cols-2">
                        <div><div className="mb-0.5 text-[10px] font-semibold uppercase text-green">Evidence</div><List items={c.evidence} /></div>
                        <div><div className="mb-0.5 text-[10px] font-semibold uppercase text-red">Counter-evidence</div><List items={c.counter_evidence} /></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section title="Observed facts" count={d.observed_facts?.length}>
              {!d.observed_facts?.length ? <span className="text-dim">none</span> : (
                <ul className="space-y-1">
                  {d.observed_facts.map((f, i) => (
                    <li key={i} className="flex items-start gap-2"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted" /><span>{f.text} {f.region && <span className="text-dim">({f.region})</span>} <ImgRef index={f.image_index} onFocusImage={onFocusImage} /></span></li>
                  ))}
                </ul>
              )}
              {(d.alternative_explanations?.length ?? 0) > 0 && (
                <div className="mt-2"><div className="mb-0.5 text-[10px] font-semibold uppercase text-muted">Alternative explanations</div><List items={d.alternative_explanations} /></div>
              )}
            </Section>

            {clothing && (
              <Section title="Clothing detail">
                <KV rows={[
                  ["Garment", clothing.garment_type],
                  ["Brand / maker", clothing.brand_or_manufacturer ? <span key="b">{clothing.brand_or_manufacturer} <span className="num text-dim">{conf(clothing.brand_confidence)}</span></span> : null],
                  ["Labels transcribed", clothing.label_texts?.length ? (
                    <ul key="lt" className="space-y-0.5">{clothing.label_texts.map((t, i) => <li key={i}><span className="num rounded bg-elev-2 px-1">{t.text}</span> <span className="text-dim">{t.label_type}{t.legibility ? ` · ${t.legibility}` : ""}</span> <ImgRef index={t.image_index} onFocusImage={onFocusImage} /></li>)}</ul>
                  ) : null],
                  ["Era", clothing.era_estimate ? <span key="e">{clothing.era_estimate} <span className="text-dim">— {clothing.era_evidence?.join("; ") || "no evidence listed"}</span></span> : null],
                  ["Fabric / construction", <List key="f" items={clothing.fabric_and_construction} />],
                  ["Stitching / seams", <List key="s" items={clothing.stitching_and_seams} />],
                  ["Country", clothing.country_of_manufacture ? <span key="c">{clothing.country_of_manufacture} <span className="text-dim">({clothing.country_evidence || "unverified"})</span></span> : null],
                  ["Graphics / prints", clothing.graphics_or_prints],
                  ["Model names / numbers", <List key="m" items={clothing.model_names_or_numbers} />],
                  ["Size / measurements", clothing.size_and_measurements],
                  ["Collectible traits", <List key="cc" items={clothing.collectible_characteristics} />],
                  ["Authenticity indicators", <List key="ai" items={clothing.authenticity_indicators} />],
                  ["Inspect in hand", <List key="ip" items={clothing.expert_inspection_points} />],
                ]} />
              </Section>
            )}

            {jewelry && (
              <Section title="Jewelry detail">
                <KV rows={[
                  ["Type", jewelry.jewelry_type],
                  ["Potential maker", jewelry.potential_maker ? <span key="pm">{jewelry.potential_maker} <span className="num text-dim">{conf(jewelry.maker_confidence)}</span></span> : null],
                  ["Maker's marks", jewelry.makers_marks?.length ? <ul key="mm" className="space-y-0.5">{jewelry.makers_marks.map((t, i) => <li key={i}><span className="num rounded bg-elev-2 px-1">{t.text}</span> <span className="text-dim">{t.label_type}{t.legibility ? ` · ${t.legibility}` : ""}</span> <ImgRef index={t.image_index} onFocusImage={onFocusImage} /></li>)}</ul> : null],
                  ["Hallmarks / inscriptions", jewelry.hallmarks_and_inscriptions?.length ? <ul key="hm" className="space-y-0.5">{jewelry.hallmarks_and_inscriptions.map((t, i) => <li key={i}><span className="num rounded bg-elev-2 px-1">{t.text}</span> <span className="text-dim">{t.label_type}{t.legibility ? ` · ${t.legibility}` : ""}</span> <ImgRef index={t.image_index} onFocusImage={onFocusImage} /></li>)}</ul> : null],
                  ["Materials (hypotheses)", jewelry.materials?.length ? (
                    <ul key="mat" className="space-y-1">{jewelry.materials.map((m, i) => (
                      <li key={i}><span className="font-medium">{m.material}</span> <span className="num text-dim">{conf(m.confidence)}</span>{m.basis?.length ? <span className="text-muted"> — basis: {m.basis.join("; ")}</span> : null}{m.verification_needed && <div className="text-xs text-amber"><AlertTriangle size={10} className="inline" /> verify: {m.verification_needed}</div>}</li>
                    ))}</ul>
                  ) : null],
                  ["Stones / other", <List key="st" items={jewelry.stones_or_other_materials} />],
                  ["Design", <List key="dc" items={jewelry.design_characteristics} />],
                  ["Construction", <List key="ct" items={jewelry.construction_techniques} />],
                  ["Period", jewelry.stylistic_period ? <span key="p">{jewelry.stylistic_period} <span className="text-dim">— {jewelry.period_evidence?.join("; ") || "no evidence listed"}</span></span> : null],
                  ["Collectible traits", <List key="cc" items={jewelry.collectible_characteristics} />],
                  ["Authenticity concerns", jewelry.authenticity_concerns?.length ? <ul key="ac" className="list-disc pl-4 text-amber">{jewelry.authenticity_concerns.map((x, i) => <li key={i}>{x}</li>)}</ul> : null],
                  ["Lot components", jewelry.lot_components?.length ? <List key="lc" items={jewelry.lot_components.map((x) => typeof x === "string" ? x : JSON.stringify(x))} /> : null],
                  ["Melt value", jewelry.melt_value_note],
                ]} />
              </Section>
            )}

            <Section title="Condition & value indicators">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <div className="mb-1 text-[10px] font-semibold uppercase text-muted">Condition issues</div>
                  {!d.condition_issues?.length ? <span className="text-dim">none noted</span> : (
                    <ul className="space-y-0.5">{d.condition_issues.map((c, i) => <li key={i}><Badge tone={c.severity === "major" || c.severity === "severe" ? "red" : c.severity === "moderate" ? "amber" : "gray"}>{c.severity || "?"}</Badge> {c.issue} <ImgRef index={c.image_index} onFocusImage={onFocusImage} /></li>)}</ul>
                  )}
                </div>
                <div>
                  <div className="mb-1 text-[10px] font-semibold uppercase text-muted">Value indicators</div>
                  {!d.value_indicators?.length ? <span className="text-dim">none</span> : (
                    <ul className="space-y-0.5">{d.value_indicators.map((v, i) => <li key={i}><StrengthBadge strength={v.strength} /> <span className="font-medium">{v.indicator}</span>{v.why_it_matters && <span className="text-muted"> — {v.why_it_matters}</span>}</li>)}</ul>
                  )}
                </div>
              </div>
            </Section>

            <Section title="Missing information & research queries">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <div className="mb-1 text-[10px] font-semibold uppercase text-muted">Missing information</div>
                  <List items={d.missing_information} empty="nothing flagged" />
                </div>
                <div>
                  <div className="mb-1 text-[10px] font-semibold uppercase text-muted">Research queries</div>
                  {!d.research_queries?.length ? <span className="text-dim">none</span> : (
                    <ul className="space-y-1">{d.research_queries.map((q, i) => (
                      <li key={i} className="flex flex-col gap-1 rounded border border-border p-1.5">
                        <span className="num text-xs">{q.query}</span>
                        <span className="flex items-center gap-1.5">
                          <span className="text-[10px] text-dim">{q.marketplace}{q.purpose ? ` · ${q.purpose}` : ""}</span>
                          <span className="flex-1" />
                          <CopyButton text={q.query} />
                          <a className="btn btn-xs" href={ebaySoldSearchUrl(q.query)} target="_blank" rel="noopener noreferrer" title="eBay sold listings search"><ExternalLink size={10} /> eBay sold</a>
                        </span>
                      </li>
                    ))}</ul>
                  )}
                </div>
              </div>
            </Section>

            <Section title="Reference database matches" count={d.reference_matches?.length} defaultOpen={(d.reference_matches?.length ?? 0) > 0}>
              {!d.reference_matches?.length ? <span className="text-dim">no matches</span> : (
                <table className="tbl">
                  <caption className="mb-1 text-left text-[11px] text-dim">Reference entries are identification guidance. "Typical" ranges are approximate notes (seeded or user-entered), not sold comparables, and are never used in the valuation.</caption>
                  <thead><tr><th>Entry</th><th>Type</th><th className="r">Typical</th><th>Demand</th><th>Liq.</th><th className="r">Match</th><th>Hits</th></tr></thead>
                  <tbody>{d.reference_matches.map((r) => (
                    <tr key={r.id}>
                      <td><div className="font-medium">{r.name}</div><div className="text-xs text-muted">{r.characteristics}</div></td>
                      <td className="text-xs">{titleCase(r.entry_type)}<div className="text-dim">{r.category}</div></td>
                      <td className="r num whitespace-nowrap">{money(r.typical_low, { cents: false })}–{money(r.typical_high, { cents: false })}</td>
                      <td>{r.demand}</td><td>{r.liquidity}</td>
                      <td className="r num">{num(r.match_score, 1)}</td>
                      <td className="text-[10px] text-dim">{r.hits.join(", ")}</td>
                    </tr>
                  ))}</tbody>
                </table>
              )}
            </Section>
          </Card>
        )}
        <CorrectionForm listing={listing} onUpdate={onUpdate} />
        {listing.identification_history.length > 1 && (
          <Card title={`Identification history (${listing.identification_history.length})`} bodyClass="p-0">
            <table className="tbl">
              <thead><tr><th>When</th><th>Origin</th><th>Summary</th><th className="r">Conf.</th><th>Current</th></tr></thead>
              <tbody>{listing.identification_history.map((h: IdentificationFull) => (
                <tr key={h.id}>
                  <td className="num whitespace-nowrap">{fmtDate(h.created_at)}</td>
                  <td><OriginBadge origin={h.origin} /></td>
                  <td>{h.summary}</td>
                  <td className="r num">{conf(h.confidence)}</td>
                  <td>{h.is_current ? <Badge tone="green">current</Badge> : <span className="text-dim">—</span>}</td>
                </tr>
              ))}</tbody>
            </table>
          </Card>
        )}
      </div>
      <div className="flex flex-col gap-3">
        <AnalysisRunner listing={listing} onUpdate={onUpdate} />
        <RunsList runs={listing.analysis_runs} />
      </div>
    </div>
  );
}

function CorrectionForm({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const cur = listing.identification_full;
  const [f, setF] = useState({ summary: cur?.summary ?? "", domain: listing.domain ?? "", confidence: "0.9", brand_or_maker: "", era: "", notes: "", demand_indicator: "", liquidity_indicator: "" });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: IdentificationCorrection = { summary: f.summary.trim() };
    if (f.domain) body.domain = f.domain;
    if (f.confidence !== "") body.confidence = Math.max(0, Math.min(1, Number(f.confidence)));
    if (f.brand_or_maker) body.brand_or_maker = f.brand_or_maker;
    if (f.era) body.era = f.era;
    if (f.notes) body.notes = f.notes;
    if (f.demand_indicator) body.demand_indicator = f.demand_indicator;
    if (f.liquidity_indicator) body.liquidity_indicator = f.liquidity_indicator;
    setBusy(true);
    try {
      const d = await api.correctIdentification(listing.id, body);
      onUpdate(d);
      toast.success("Identification corrected", "Stored as the current (user) identification; opportunity recomputed.");
      setOpen(false);
    } catch (err) { toast.apiError(err, "Correct identification"); } finally { setBusy(false); }
  }
  async function revert() {
    if (!confirm("Remove your correction and revert to the AI identification?")) return;
    setBusy(true);
    try {
      const d = await api.revertIdentification(listing.id);
      onUpdate(d);
      toast.info("Reverted to AI identification");
    } catch (err) { toast.apiError(err, "Revert identification"); } finally { setBusy(false); }
  }
  return (
    <Card title="Correct identification" actions={
      <div className="flex gap-1">
        {cur?.origin === "user" && <button className="btn btn-xs" onClick={revert} disabled={busy}><Undo2 size={11} /> Revert to AI</button>}
        <button className="btn btn-xs" onClick={() => setOpen((v) => !v)}>{open ? "Close" : "Correct"}</button>
      </div>
    }>
      {!open ? <p className="text-xs text-dim">Override the AI identification with what you know. Your correction becomes the current identification (origin: user) and feeds the opportunity score.</p> : (
        <form onSubmit={submit} className="grid grid-cols-2 gap-2">
          <Field label="Identification summary" className="col-span-2"><input className="input" required minLength={2} maxLength={500} value={f.summary} onChange={(e) => setF({ ...f, summary: e.target.value })} placeholder="e.g. 1980s Kingstone Designs mohair cardigan, England" /></Field>
          <Field label="Domain"><select className="input" value={f.domain} onChange={(e) => setF({ ...f, domain: e.target.value })}><option value="">keep</option><option value="clothing">clothing</option><option value="jewelry">jewelry</option></select></Field>
          <Field label="Confidence (0-1)"><input className="input" type="number" min="0" max="1" step="0.05" value={f.confidence} onChange={(e) => setF({ ...f, confidence: e.target.value })} /></Field>
          <Field label="Brand / maker"><input className="input" value={f.brand_or_maker} onChange={(e) => setF({ ...f, brand_or_maker: e.target.value })} /></Field>
          <Field label="Era"><input className="input" value={f.era} onChange={(e) => setF({ ...f, era: e.target.value })} placeholder="e.g. 1980s" /></Field>
          <Field label="Demand"><select className="input" value={f.demand_indicator} onChange={(e) => setF({ ...f, demand_indicator: e.target.value })}><option value="">keep</option><option value="high">high</option><option value="medium">medium</option><option value="low">low</option></select></Field>
          <Field label="Liquidity"><select className="input" value={f.liquidity_indicator} onChange={(e) => setF({ ...f, liquidity_indicator: e.target.value })}><option value="">keep</option><option value="high">high</option><option value="medium">medium</option><option value="low">low</option></select></Field>
          <Field label="Notes" className="col-span-2"><textarea className="input" rows={2} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
          <div className="col-span-2 flex justify-end gap-1.5">
            <button type="button" className="btn btn-sm" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-sm btn-primary" disabled={busy}>{busy ? <Spinner /> : null} Save correction</button>
          </div>
        </form>
      )}
    </Card>
  );
}

function AnalysisRunner({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const [provider, setProvider] = useState<NonNullable<AnalyzeIn["provider"]>>(listing.is_demo ? "demo" : "auto");
  const [force, setForce] = useState(false);
  const [background, setBackground] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<{ stages: AnalyzeStageSummary[]; stopped?: string } | { job_id: number; status: string } | null>(null);

  async function run(mode: AnalyzeIn["mode"]) {
    setBusy(mode); setError(null); setResult(null);
    try {
      const r = await api.analyze(listing.id, { mode, provider, force, background });
      if ("job_id" in r) {
        setResult(r);
        toast.info(`Queued background job #${r.job_id}`, "Check the Jobs page; refresh this item when it finishes.");
      } else {
        setResult(r.summary as { stages: AnalyzeStageSummary[]; stopped?: string });
        onUpdate(r.listing);
        const last = r.summary.stages[r.summary.stages.length - 1];
        toast.success(`Analysis (${mode}) finished`, last?.headline ? `${last.stage}: ${last.headline}` : `${r.summary.stages.length} stage(s) ran`);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, (e as Error).message));
      toast.apiError(e, `Analysis (${mode})`);
    } finally { setBusy(null); }
  }

  return (
    <Card title="Run analysis" actions={listing.is_demo ? <span className="text-[10px] text-demo">demo listing: use the demo provider</span> : null}>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Provider">
          <select className="input" value={provider} onChange={(e) => setProvider(e.target.value as NonNullable<AnalyzeIn["provider"]>)}>
            <option value="auto">auto (per settings)</option><option value="anthropic">anthropic</option><option value="gemini">gemini</option><option value="demo">demo (fixtures)</option>
          </select>
        </Field>
        <div className="flex flex-col justify-end gap-1 pb-0.5">
          <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} /> Force (ignore cache / gates)</label>
          <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={background} onChange={(e) => setBackground(e.target.checked)} /> Run in background job</label>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {(["auto", "triage", "deep", "prefilter"] as const).map((m) => (
          <button key={m} className={`btn btn-sm ${m === "auto" ? "btn-primary" : ""}`} onClick={() => run(m)} disabled={busy !== null} title={m === "auto" ? "prefilter → triage → deep if justified" : m === "triage" ? "cheap quick-look model" : m === "deep" ? "expensive detailed identification" : "deterministic keyword/price gate only"}>
            {busy === m ? <Spinner /> : <Play size={12} />} {titleCase(m)}
          </button>
        ))}
      </div>
      <p className="mt-1.5 text-[11px] text-dim">Triage = fast/cheap model. Deep = detailed identification with zoom. Auto escalates only if triage is interesting. Costs count against the daily budget.</p>
      {error && <ApiErrorAlert error={error} className="mt-2" />}
      {result && "stages" in result && (
        <div className="mt-2 rounded border border-border bg-elev-2/60 p-2 text-xs">
          <div className="mb-1 font-semibold">Pipeline result{result.stopped ? <span className="ml-1 font-normal text-amber">(stopped after {result.stopped})</span> : null}</div>
          <ul className="space-y-0.5">
            {result.stages.map((s, i) => (
              <li key={i} className="flex flex-wrap gap-x-2">
                <Badge tone="gray">{s.stage}</Badge>
                {s.passed !== undefined && <span className={s.passed ? "text-green" : "text-red"}>{s.passed ? "passed" : "rejected"}{s.reasons?.length ? ` · ${s.reasons.join("; ")}` : ""}</span>}
                {s.interest_score !== undefined && <span>interest <span className="num">{s.interest_score}</span>{s.escalate ? <span className="text-green"> · escalate</span> : <span className="text-dim"> · no escalation</span>}{s.cached ? <span className="text-dim"> · cached</span> : null}</span>}
                {s.headline && <span>{s.headline} <span className="num text-dim">{conf(s.confidence)}</span></span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result && "job_id" in result && <Alert kind="info" className="mt-2">Background job #{result.job_id} queued ({result.status}).</Alert>}
    </Card>
  );
}

function RunsList({ runs }: { runs: AnalysisRun[] }) {
  const [openId, setOpenId] = useState<number | null>(null);
  return (
    <Card title={`Analysis runs (${runs.length})`} bodyClass="p-0">
      {runs.length === 0 ? <p className="p-3 text-xs text-dim">No runs yet.</p> : (
        <div className="scrollbar-thin max-h-[520px] overflow-auto">
          <table className="tbl">
            <thead><tr><th>Stage</th><th>Provider / model</th><th>Status</th><th className="r">Cost</th><th>When</th></tr></thead>
            <tbody>
              {runs.map((r) => (
                <RunRow key={r.id} r={r} open={openId === r.id} onToggle={() => setOpenId(openId === r.id ? null : r.id)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function RunRow({ r, open, onToggle }: { r: AnalysisRun; open: boolean; onToggle: () => void }) {
  return (
    <>
      <tr className="cursor-pointer" onClick={onToggle} tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") onToggle(); }}>
        <td><div className="flex items-center gap-1">{open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}<span className="font-medium">{r.stage}</span>{r.is_demo && <DemoBadge />}</div></td>
        <td className="text-xs"><div>{r.provider || "—"}</div><div className="num text-dim">{r.model || ""}</div></td>
        <td><StatusBadge status={r.status} />{r.error && <div className="mt-0.5 max-w-[180px] truncate text-[10px] text-red" title={r.error}>{r.error}</div>}</td>
        <td className="r num text-xs">{r.est_cost_usd != null ? `$${r.est_cost_usd.toFixed(3)}` : "—"}</td>
        <td className="num whitespace-nowrap text-xs" title={fmtDate(r.created_at)}>{relTime(r.created_at)}</td>
      </tr>
      {open && (
        <tr><td colSpan={5} className="bg-elev-2/40">
          <div className="num mb-1 text-[11px] text-muted">run #{r.id} · tokens {num(r.tokens_in)} in / {num(r.tokens_out)} out · {num(r.duration_ms)} ms · {fmtDate(r.created_at)}{r.input_hash ? ` · hash ${r.input_hash.slice(0, 10)}` : ""}</div>
          {r.error && <div className="mb-1 text-xs text-red"><RotateCcw size={10} className="inline" /> {r.error}</div>}
          <Pre data={r.output ?? {}} />
        </td></tr>
      )}
    </>
  );
}
