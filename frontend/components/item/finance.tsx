"use client";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { money, numOrNull, pct, titleCase } from "@/lib/format";
import type { FinanceOverrides, FinanceQuery, FinanceResponse, FinanceScenario, ListingDetail, SettingsObject } from "@/lib/types";
import { Badge, EvidenceBadge } from "@/components/ui/badges";
import { Alert, ApiErrorAlert, Card, Field, Spinner, Stat } from "@/components/ui/primitives";

type Inputs = {
  platform: string; bid: string; resale_price: string;
  incoming_shipping: string; outgoing_shipping: string; sales_tax_pct: string; cleaning_repair_cost: string; packaging_cost: string;
  min_profit_usd: string; min_roi_pct: string; max_capital_at_risk_usd: string;
};

type NumericOverrideKey = Exclude<keyof FinanceOverrides, "platform">;
const OVERRIDE_KEYS: NumericOverrideKey[] = ["incoming_shipping", "outgoing_shipping", "sales_tax_pct", "cleaning_repair_cost", "packaging_cost", "min_profit_usd", "min_roi_pct", "max_capital_at_risk_usd"];

export function FinancePanel({ listing, settings }: { listing: ListingDetail; settings: SettingsObject | undefined }) {
  const fin = listing.opportunity?.finance;
  const initial = useMemo<Inputs>(() => ({
    platform: fin?.platform || settings?.default_platform || "ebay",
    bid: listing.current_bid?.toString() ?? "",
    resale_price: "",
    incoming_shipping: "", outgoing_shipping: "", sales_tax_pct: "", cleaning_repair_cost: "", packaging_cost: "",
    min_profit_usd: "", min_roi_pct: "", max_capital_at_risk_usd: "",
  }), [fin?.platform, settings?.default_platform, listing.current_bid]);
  const [inp, setInp] = useState<Inputs>(initial);
  const [data, setData] = useState<FinanceResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const query = useMemo<FinanceQuery>(() => {
    const overrides: FinanceOverrides = {};
    for (const k of OVERRIDE_KEYS) { const v = numOrNull(inp[k]); if (v !== null) overrides[k] = v; }
    return { bid: numOrNull(inp.bid), platform: inp.platform || null, resale_price: numOrNull(inp.resale_price), overrides, sensitivity: true };
  }, [inp]);
  const key = JSON.stringify(query);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const r = await api.finance(listing.id, JSON.parse(key) as FinanceQuery);
        if (!cancelled) { setData(r); setError(null); }
      } catch (e) {
        if (!cancelled) setError(e instanceof ApiError ? e : new ApiError(0, (e as Error).message));
      } finally { if (!cancelled) setLoading(false); }
    }, 300);
    return () => { cancelled = true; clearTimeout(t); };
  }, [key, listing.id, listing.last_updated_at, listing.valuation_full?.id]);

  const set = (k: keyof Inputs) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setInp((p) => ({ ...p, [k]: e.target.value }));
  const exp = data?.scenarios.expected;
  const ra = data?.risk_adjusted;
  const platforms = settings?.platforms ?? {};
  const overMax = exp && data ? data.bid_used > exp.max_bid : false;
  const unknown = exp?.unknown_costs ?? [];
  const assumed = exp?.assumed_costs ?? {};

  return (
    <div className="grid gap-3 xl:grid-cols-[320px_1fr]">
      <Card title="What-if inputs" actions={<button className="btn btn-xs" onClick={() => setInp(initial)} title="Reset to listing values"><RotateCcw size={11} /> Reset</button>}>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Resale platform" className="col-span-2">
            <select className="input" value={inp.platform} onChange={set("platform")}>
              {Object.entries(platforms).map(([k, p]) => <option key={k} value={k}>{p.label} ({p.final_value_fee_pct}% + {p.payment_processing_pct}%)</option>)}
              {!platforms[inp.platform] && <option value={inp.platform}>{inp.platform}</option>}
            </select>
          </Field>
          <Field label="Your bid" hint={`listing: ${money(listing.current_bid)}`}><input className="input" type="number" step="1" min="0" value={inp.bid} onChange={set("bid")} /></Field>
          <Field label="Resale price" hint={`expected: ${money(listing.valuation?.expected, { cents: false })}`}><input className="input" type="number" step="1" min="0" placeholder="valuation" value={inp.resale_price} onChange={set("resale_price")} /></Field>
          <div className="col-span-2 mt-1 label">Cost overrides (blank = settings / listing default)</div>
          <Field label="Incoming shipping" hint={`listing: ${money(listing.shipping_cost)}`}><input className="input" type="number" step="0.01" min="0" value={inp.incoming_shipping} onChange={set("incoming_shipping")} /></Field>
          <Field label="Outgoing shipping"><input className="input" type="number" step="0.01" min="0" value={inp.outgoing_shipping} onChange={set("outgoing_shipping")} placeholder={assumed.outgoing_shipping?.toString() ?? ""} /></Field>
          <Field label="Sales tax %"><input className="input" type="number" step="0.1" min="0" value={inp.sales_tax_pct} onChange={set("sales_tax_pct")} /></Field>
          <Field label="Cleaning / repair"><input className="input" type="number" step="0.01" min="0" value={inp.cleaning_repair_cost} onChange={set("cleaning_repair_cost")} /></Field>
          <Field label="Packaging"><input className="input" type="number" step="0.01" min="0" value={inp.packaging_cost} onChange={set("packaging_cost")} /></Field>
          <div className="col-span-2 mt-1 label">Threshold overrides</div>
          <Field label="Min profit $"><input className="input" type="number" step="1" min="0" value={inp.min_profit_usd} onChange={set("min_profit_usd")} placeholder={data?.thresholds.min_profit_usd.toString()} /></Field>
          <Field label="Min ROI %"><input className="input" type="number" step="1" min="0" value={inp.min_roi_pct} onChange={set("min_roi_pct")} placeholder={data?.thresholds.min_roi_pct.toString()} /></Field>
          <Field label="Max capital at risk $" className="col-span-2"><input className="input" type="number" step="1" min="0" value={inp.max_capital_at_risk_usd} onChange={set("max_capital_at_risk_usd")} placeholder={data?.thresholds.max_capital_at_risk_usd.toString()} /></Field>
        </div>
        {data && Object.keys(data.assumptions_used.listing_overrides).length > 0 && (
          <p className="mt-2 text-[11px] text-muted">Listing-level assumptions in effect: <span className="num">{Object.entries(data.assumptions_used.listing_overrides).map(([k, v]) => `${k}=${v}`).join(", ")}</span></p>
        )}
      </Card>

      <div className="flex flex-col gap-3">
        {error && <ApiErrorAlert error={error} />}
        {!data && !error && <div className="flex items-center gap-2 text-sm text-muted"><Spinner /> Computing…</div>}
        {data && exp && (
          <>
            <div className={`transition ${loading ? "opacity-60" : ""}`}>
              {unknown.length > 0 && (
                <Alert kind="warning" title={`Unknown costs: ${unknown.map(titleCase).join(", ")}`} className="mb-2">
                  Finance is incomplete until these are known. Set them in the inputs or in Settings → acquisition / resale defaults.
                </Alert>
              )}
              {Object.keys(assumed).length > 0 && (
                <p className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px] text-muted"><AlertTriangle size={11} className="text-amber" /> Assumed costs (from settings, not confirmed): {Object.entries(assumed).map(([k, v]) => <span key={k} className="num rounded bg-elev-2 px-1">{titleCase(k)} {money(v)}</span>)}</p>
              )}
              <div className="grid grid-cols-2 gap-1.5 md:grid-cols-4">
                <Stat label="Expected profit" value={money(exp.profit)} tone={exp.profit >= 0 ? "green" : "red"} sub={`${pct(exp.roi_pct, 1)} ROI · net margin ${pct(exp.net_margin_pct, 1)}`} />
                <Stat label="Max bid" value={money(exp.max_bid)} tone={overMax ? "red" : "blue"} sub={<>binding: <span className="font-medium">{exp.max_bid_binding_constraint || "—"}</span>{overMax ? <span className="text-red"> · your bid is over max</span> : null}</>} />
                <Stat label="Break-even bid" value={money(exp.break_even_bid)} sub="profit = 0 at expected resale" />
                <Stat label="Risk-adjusted profit" value={money(ra?.profit)} tone={(ra?.profit ?? 0) >= 0 ? "green" : "red"} sub={ra?.meta?.label ?? "heuristic, uncalibrated"} />
              </div>
            </div>

            <div className={`grid gap-3 lg:grid-cols-2 ${loading ? "opacity-60" : ""}`}>
              <Card title={`Expected scenario @ bid ${money(data.bid_used)} on ${platforms[data.platform]?.label ?? data.platform}`} bodyClass="p-0">
                <table className="tbl">
                  <tbody>
                    <tr><td className="text-muted">Bid</td><td className="r num">{money(exp.acquisition_breakdown.bid)}</td></tr>
                    <tr><td className="text-muted">Buyer premium</td><td className="r num">{money(exp.acquisition_breakdown.buyer_premium)}</td></tr>
                    <tr><td className="text-muted">Sales tax</td><td className="r num">{money(exp.acquisition_breakdown.sales_tax)}</td></tr>
                    <tr><td className="text-muted">Incoming shipping</td><td className="r num">{money(exp.acquisition_breakdown.incoming_shipping)}</td></tr>
                    <tr><td className="text-muted">Handling fee</td><td className="r num">{money(exp.acquisition_breakdown.handling_fee)}</td></tr>
                    <tr><td className="text-muted">Other</td><td className="r num">{money(exp.acquisition_breakdown.other)}</td></tr>
                    <tr className="font-semibold"><td>Acquisition total</td><td className="r num">{money(exp.acquisition_total)}</td></tr>
                    <tr><td className="pt-3 text-muted">Resale price</td><td className="r num pt-3">{money(exp.resale_price)}</td></tr>
                    <tr><td className="text-muted">Selling fees</td><td className="r num text-red">−{money(exp.selling_fees)}</td></tr>
                    <tr><td className="text-muted">Resale costs (ship/pack/clean)</td><td className="r num text-red">−{money(exp.resale_costs)}</td></tr>
                    <tr className="font-semibold"><td>Net proceeds</td><td className="r num">{money(exp.net_proceeds)}</td></tr>
                    <tr className="font-semibold"><td>Profit</td><td className={`r num ${exp.profit >= 0 ? "text-green" : "text-red"}`}>{money(exp.profit)}</td></tr>
                    <tr><td className="text-muted">ROI / gross margin / net margin</td><td className="r num">{pct(exp.roi_pct, 1)} / {pct(exp.gross_margin_pct, 1)} / {pct(exp.net_margin_pct, 1)}</td></tr>
                  </tbody>
                </table>
                {exp.notes.length > 0 && <ul className="p-2 text-xs text-amber">{exp.notes.map((n, i) => <li key={i}>• {n}</li>)}</ul>}
              </Card>

              <div className="flex flex-col gap-3">
                <Card title="Scenarios" bodyClass="p-0">
                  <table className="tbl">
                    <thead><tr><th>Scenario</th><th className="r">Resale</th><th className="r">Profit</th><th className="r">ROI</th><th className="r">Max bid</th><th>Constraint</th></tr></thead>
                    <tbody>
                      {(["conservative", "expected", "optimistic"] as const).map((k) => <ScenarioRow key={k} name={k} s={data.scenarios[k]} />)}
                      {ra && <ScenarioRow name="risk-adjusted" s={ra} highlight />}
                    </tbody>
                  </table>
                  {ra?.meta && (
                    <p className="p-2 text-[11px] text-dim">
                      Risk-adjusted = weights {ra.meta.scenario_weights?.map((w) => (w * 100).toFixed(0) + "%").join("/")} (cons/exp/opt) for <strong>{ra.meta.evidence_quality}</strong> evidence, minus {ra.meta.confidence_haircut_pct}% identification-confidence haircut{ra.meta.holding_cost ? `, ${money(ra.meta.holding_cost)} holding cost over ~${ra.meta.estimated_months_to_sell} mo` : `, ~${ra.meta.estimated_months_to_sell} mo to sell`}. <em>{ra.meta.label}</em>.
                    </p>
                  )}
                </Card>
                <Card title="Valuation used">
                  <div className="flex flex-wrap items-center gap-1.5 text-xs">
                    <Badge tone="gray">{data.valuation.method}</Badge>
                    <EvidenceBadge quality={data.valuation.evidence_quality} speculative={data.valuation.is_speculative} />
                    <span className="num text-muted">{money(data.valuation.conservative, { cents: false })} / {money(data.valuation.expected, { cents: false })} / {money(data.valuation.optimistic, { cents: false })}</span>
                    <span className="text-dim">· {data.valuation.n_sold_comps} sold comps</span>
                  </div>
                  {data.valuation.notes.length > 0 && <ul className="mt-1 text-xs text-amber">{data.valuation.notes.map((n, i) => <li key={i}>• {n}</li>)}</ul>}
                  <div className="num mt-2 text-[11px] text-dim">Thresholds: min profit {money(data.thresholds.min_profit_usd)} · min ROI {pct(data.thresholds.min_roi_pct)} · max capital {money(data.thresholds.max_capital_at_risk_usd)} · bid step {money(data.thresholds.bid_increment)}</div>
                </Card>
              </div>
            </div>

            <SensitivityGrid data={data} loading={loading} />
          </>
        )}
      </div>
    </div>
  );
}

function ScenarioRow({ name, s, highlight }: { name: string; s: FinanceScenario; highlight?: boolean }) {
  return (
    <tr className={highlight ? "bg-accent/5 font-medium" : ""}>
      <td className="capitalize">{name}{!s.complete && <Badge tone="amber" className="ml-1">incomplete</Badge>}</td>
      <td className="r num">{money(s.resale_price)}</td>
      <td className={`r num ${s.profit >= 0 ? "text-green" : "text-red"}`}>{money(s.profit)}</td>
      <td className="r num">{pct(s.roi_pct, 0)}</td>
      <td className="r num">{money(s.max_bid)}</td>
      <td className="text-xs text-muted">{s.max_bid_binding_constraint || "—"}</td>
    </tr>
  );
}

function SensitivityGrid({ data, loading }: { data: FinanceResponse; loading: boolean }) {
  const [metric, setMetric] = useState<"profit" | "max_bid" | "roi_pct">("profit");
  const rows = Array.from(new Set(data.sensitivity.map((c) => c.resale_price))).sort((a, b) => a - b);
  const cols = Array.from(new Set(data.sensitivity.map((c) => c.incoming_shipping))).sort((a, b) => a - b);
  const map = new Map(data.sensitivity.map((c) => [`${c.resale_price}|${c.incoming_shipping}`, c]));
  if (!rows.length) return null;
  const thr = data.thresholds;
  return (
    <Card title="Sensitivity: resale price × incoming shipping" actions={
      <div className="flex gap-1">
        {(["profit", "max_bid", "roi_pct"] as const).map((m) => <button key={m} className={`btn btn-xs ${metric === m ? "btn-primary" : ""}`} onClick={() => setMetric(m)}>{m === "profit" ? "Profit" : m === "max_bid" ? "Max bid" : "ROI"}</button>)}
      </div>
    } bodyClass={`p-0 ${loading ? "opacity-60" : ""}`}>
      <div className="scrollbar-thin overflow-x-auto">
        <table className="tbl">
          <thead><tr><th>Resale ↓ / Ship →</th>{cols.map((c) => <th key={c} className="r">{money(c)}</th>)}</tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r}>
                <td className="num font-medium">{money(r, { cents: false })}{data.valuation.expected === r && <span className="ml-1 text-[10px] text-blue">exp.</span>}</td>
                {cols.map((c) => {
                  const cell = map.get(`${r}|${c}`);
                  if (!cell) return <td key={c} className="r text-dim">—</td>;
                  const v = cell[metric];
                  const good = metric === "profit" ? v >= thr.min_profit_usd : metric === "roi_pct" ? v >= thr.min_roi_pct : v >= data.bid_used;
                  const bad = metric === "profit" ? v < 0 : metric === "roi_pct" ? v < 0 : v <= 0;
                  const cls = bad ? "bg-red/15 text-red" : good ? "bg-green/15 text-green" : "bg-amber/10 text-amber";
                  return (
                    <td key={c} className={`r num ${cls}`} title={`resale ${money(r)} · ship ${money(c)}: profit ${money(cell.profit)}, max bid ${money(cell.max_bid)}, ROI ${pct(cell.roi_pct)}`}>
                      {metric === "roi_pct" ? pct(v, 0) : money(v, { cents: false })}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="p-2 text-[11px] text-dim">Green meets thresholds (min profit {money(thr.min_profit_usd)} / min ROI {pct(thr.min_roi_pct)} / max bid ≥ bid used), amber is below threshold, red is a loss.</p>
    </Card>
  );
}
