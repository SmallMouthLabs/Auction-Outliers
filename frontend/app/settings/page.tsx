"use client";
import { RotateCcw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { titleCase } from "@/lib/format";
import type { PlatformConfig, SettingsObject } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { Badge } from "@/components/ui/badges";
import { Alert, ApiErrorAlert, Card, Field, KV, Skeleton, Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

type Section = keyof SettingsObject;
const SECTIONS: Section[] = ["platforms", "default_platform", "acquisition", "resale", "thresholds", "risk", "ranking", "analysis", "notifications", "model_pricing_usd_per_1m"];

function clone<T>(x: T): T { return JSON.parse(JSON.stringify(x)); }
function same(a: unknown, b: unknown) { return JSON.stringify(a) === JSON.stringify(b); }

export default function SettingsPage() {
  const toast = useToast();
  const s = useApi(() => api.settings(), []);
  const [draft, setDraft] = useState<SettingsObject | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  useEffect(() => { if (s.data) setDraft(clone(s.data.settings)); }, [s.data]);

  const changed = useMemo(() => {
    if (!draft || !s.data) return [] as Section[];
    return SECTIONS.filter((k) => !same(draft[k], s.data!.settings[k]));
  }, [draft, s.data]);

  async function save() {
    if (!draft || !changed.length) return;
    const patch: Partial<SettingsObject> = {};
    for (const k of changed) (patch as Record<string, unknown>)[k] = draft[k];
    setBusy("save");
    try {
      const r = await api.putSettings(patch);
      // PUT returns only { settings }; keep env / defaults / credentials from the last GET
      s.setData((prev) => (prev ? { ...prev, settings: r.settings } : prev));
      toast.success("Settings saved", `Updated: ${changed.join(", ")}. Opportunities will use the new values on next recompute.`);
    } catch (e) { toast.apiError(e, "Save settings"); } finally { setBusy(null); }
  }
  async function reset() {
    if (!confirm("Reset ALL settings to defaults?")) return;
    setBusy("reset");
    try { const r = await api.resetSettings(); s.setData((prev) => (prev ? { ...prev, settings: r.settings } : prev)); toast.info("Settings reset to defaults"); }
    catch (e) { toast.apiError(e, "Reset settings"); } finally { setBusy(null); }
  }

  if (s.error && !s.data) return <ApiErrorAlert error={s.error} />;
  if (!draft || !s.data) return <div className="flex flex-col gap-2"><Skeleton className="h-10" /><Skeleton className="h-64" /></div>;
  const env = s.data.env;
  const creds = s.data.credentials_configured;
  const upd = <K extends Section>(k: K, v: SettingsObject[K]) => setDraft((d) => d ? { ...d, [k]: v } : d);

  return (
    <div className="flex flex-col gap-3">
      <div className="sticky top-[38px] z-10 -mx-4 flex items-center justify-between gap-2 border-b border-border bg-bg/95 px-4 py-2 backdrop-blur">
        <div>
          <h1 className="text-lg font-semibold">Settings</h1>
          <p className="text-xs text-muted">{changed.length ? <span className="text-amber">Unsaved changes in: {changed.join(", ")}</span> : "All changes saved. Only changed sections are sent (PUT /api/settings)."}</p>
        </div>
        <div className="flex gap-1.5">
          <button className="btn btn-sm" onClick={() => setDraft(clone(s.data!.settings))} disabled={!changed.length}>Discard</button>
          <button className="btn btn-sm btn-danger" onClick={reset} disabled={busy !== null}><RotateCcw size={13} /> Reset all to defaults</button>
          <button className="btn btn-sm btn-primary" onClick={save} disabled={busy !== null || !changed.length}>{busy === "save" ? <Spinner /> : <Save size={13} />} Save {changed.length ? `(${changed.length})` : ""}</button>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card title="Environment (read-only, from backend .env)" className="xl:col-span-2">
          <div className="grid gap-3 md:grid-cols-2">
            <KV rows={[
              ["Triage provider / model", <span key="t" className="num">{env.triage_provider} / {env.triage_model || "default"}</span>],
              ["Deep provider / model", <span key="d" className="num">{env.deep_provider} / {env.deep_model || "default"}</span>],
              ["Daily AI budget", <span key="b" className="num">${env.daily_budget_usd.toFixed(2)}</span>],
              ["Per-listing budget", <span key="pl" className="num">${env.per_listing_budget_usd.toFixed(2)}</span>],
              ["Max zoom calls", <span key="z" className="num">{env.max_zoom_calls}</span>],
              ["Unofficial SGW API", env.enable_unofficial_sgw_api ? "enabled" : "disabled"],
              ["IMAP host / user", <span key="i" className="num">{env.imap_host || "—"} / {env.imap_user || "—"}</span>],
              ["Buyer ZIP", env.buyer_zip || "—"],
            ]} />
            <div>
              <div className="label">Credentials configured</div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(creds).map(([k, v]) => <Badge key={k} tone={v ? "green" : "amber"}>{k}: {v ? "set" : "missing"}</Badge>)}
              </div>
              <Alert kind="info" className="mt-2">API keys and IMAP credentials are never shown or editable here. Set <code className="num">ANTHROPIC_API_KEY</code>, <code className="num">GEMINI_API_KEY</code>, <code className="num">EBAY_CLIENT_ID/SECRET</code>, <code className="num">OUTLIER_IMAP_*</code> and budgets in <code className="num">backend/.env</code> and restart the backend.</Alert>
            </div>
          </div>
        </Card>

        <Card title="Resale platforms (fee configs)" className="xl:col-span-2" actions={
          <Field label="Default platform" className="flex items-center gap-2 [&>label]:mb-0">
            <select className="input w-auto py-0.5" value={draft.default_platform} onChange={(e) => upd("default_platform", e.target.value)}>{Object.entries(draft.platforms).map(([k, p]) => <option key={k} value={k}>{p.label}</option>)}</select>
          </Field>
        } bodyClass="p-0">
          <div className="scrollbar-thin overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Key</th><th>Label</th><th className="r">Final value fee %</th><th className="r">Per-order fee</th><th className="r">Payment proc. %</th><th className="r">Payment fixed</th><th className="r">Listing fee</th><th>Seller pays ship</th><th>Note</th></tr></thead>
              <tbody>
                {Object.entries(draft.platforms).map(([k, p]) => {
                  const set = (patch: Partial<PlatformConfig>) => upd("platforms", { ...draft.platforms, [k]: { ...p, ...patch } });
                  const nf = (field: keyof PlatformConfig) => <input className="input num w-20 py-0.5 text-right" type="number" step="0.01" value={p[field] as number} onChange={(e) => set({ [field]: Number(e.target.value) } as Partial<PlatformConfig>)} />;
                  return (
                    <tr key={k}>
                      <td className="num">{k}</td>
                      <td><input className="input w-24 py-0.5" value={p.label} onChange={(e) => set({ label: e.target.value })} /></td>
                      <td className="r">{nf("final_value_fee_pct")}</td><td className="r">{nf("per_order_fee")}</td><td className="r">{nf("payment_processing_pct")}</td><td className="r">{nf("payment_processing_fixed")}</td><td className="r">{nf("listing_fee")}</td>
                      <td><input type="checkbox" checked={p.seller_pays_shipping} onChange={(e) => set({ seller_pays_shipping: e.target.checked })} /></td>
                      <td><input className="input w-full min-w-[200px] py-0.5 text-xs" value={p.note} onChange={(e) => set({ note: e.target.value })} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Acquisition assumptions">
          <div className="grid grid-cols-2 gap-2">
            <NumField label="Buyer premium %" value={draft.acquisition.buyer_premium_pct} onChange={(v) => upd("acquisition", { ...draft.acquisition, buyer_premium_pct: v ?? 0 })} />
            <NumField label="Sales tax %" value={draft.acquisition.sales_tax_pct} onChange={(v) => upd("acquisition", { ...draft.acquisition, sales_tax_pct: v ?? 0 })} />
            <NumField label="Default incoming shipping" value={draft.acquisition.default_incoming_shipping} nullable hint="blank = unknown (flagged in finance)" onChange={(v) => upd("acquisition", { ...draft.acquisition, default_incoming_shipping: v })} />
            <NumField label="Default handling fee" value={draft.acquisition.default_handling_fee} nullable onChange={(v) => upd("acquisition", { ...draft.acquisition, default_handling_fee: v })} />
            <NumField label="Bid increment" value={draft.acquisition.bid_increment} onChange={(v) => upd("acquisition", { ...draft.acquisition, bid_increment: v ?? 1 })} />
          </div>
        </Card>

        <Card title="Resale costs">
          <div className="grid grid-cols-2 gap-2">
            <NumField label="Clothing outgoing shipping" value={draft.resale.clothing_outgoing_shipping} onChange={(v) => upd("resale", { ...draft.resale, clothing_outgoing_shipping: v ?? 0 })} />
            <NumField label="Jewelry outgoing shipping" value={draft.resale.jewelry_outgoing_shipping} onChange={(v) => upd("resale", { ...draft.resale, jewelry_outgoing_shipping: v ?? 0 })} />
            <NumField label="Packaging cost" value={draft.resale.packaging_cost} onChange={(v) => upd("resale", { ...draft.resale, packaging_cost: v ?? 0 })} />
            <NumField label="Default cleaning cost" value={draft.resale.default_cleaning_cost} onChange={(v) => upd("resale", { ...draft.resale, default_cleaning_cost: v ?? 0 })} />
            <NumField label="Holding cost / month" value={draft.resale.holding_cost_per_month} onChange={(v) => upd("resale", { ...draft.resale, holding_cost_per_month: v ?? 0 })} />
          </div>
        </Card>

        <Card title="Decision thresholds">
          <div className="grid grid-cols-3 gap-2">
            <NumField label="Min profit $" value={draft.thresholds.min_profit_usd} onChange={(v) => upd("thresholds", { ...draft.thresholds, min_profit_usd: v ?? 0 })} />
            <NumField label="Min ROI %" value={draft.thresholds.min_roi_pct} onChange={(v) => upd("thresholds", { ...draft.thresholds, min_roi_pct: v ?? 0 })} />
            <NumField label="Max capital at risk $" value={draft.thresholds.max_capital_at_risk_usd} onChange={(v) => upd("thresholds", { ...draft.thresholds, max_capital_at_risk_usd: v ?? 0 })} />
          </div>
          <p className="mt-2 text-[11px] text-dim">Max recommended bid = the highest bid that still satisfies all three.</p>
        </Card>

        <Card title="Risk heuristics" actions={<Badge tone="gray">heuristic, uncalibrated</Badge>}>
          <div className="label">Scenario weights by evidence quality (conservative / expected / optimistic)</div>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(draft.risk.scenario_weights_by_evidence).map(([q, w]) => (
              <div key={q}>
                <div className="mb-0.5 text-xs text-muted">{q}</div>
                <div className="flex gap-1">{w.map((x, i) => <input key={i} className="input num w-full px-1 py-0.5 text-center" type="number" step="0.05" min="0" max="1" value={x} onChange={(e) => { const nw = [...w]; nw[i] = Number(e.target.value); upd("risk", { ...draft.risk, scenario_weights_by_evidence: { ...draft.risk.scenario_weights_by_evidence, [q]: nw } }); }} />)}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <NumField label="Identification confidence haircut" hint="fraction of (1 - confidence) deducted" value={draft.risk.identification_confidence_haircut} onChange={(v) => upd("risk", { ...draft.risk, identification_confidence_haircut: v ?? 0 })} />
            <div>
              <div className="label">Est. months to sell by liquidity</div>
              <div className="flex gap-1">{Object.entries(draft.risk.estimated_months_to_sell).map(([k, v]) => <Field key={k} label={k} className="flex-1"><input className="input num py-0.5" type="number" step="0.5" min="0" value={v} onChange={(e) => upd("risk", { ...draft.risk, estimated_months_to_sell: { ...draft.risk.estimated_months_to_sell, [k]: Number(e.target.value) } })} /></Field>)}</div>
            </div>
          </div>
        </Card>

        <Card title="Ranking weights" actions={<Badge tone="gray">heuristic weights, uncalibrated</Badge>}>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {Object.entries(draft.ranking.weights).map(([k, v]) => (
              <label key={k} className="flex items-center justify-between gap-2 text-xs"><span>{titleCase(k)}</span><input className="input num w-20 py-0.5 text-right" type="number" step="0.01" min="0" max="1" value={v} onChange={(e) => upd("ranking", { ...draft.ranking, weights: { ...draft.ranking.weights, [k]: Number(e.target.value) } })} /></label>
            ))}
          </div>
          <div className="num mt-1 text-[11px] text-dim">sum = {Object.values(draft.ranking.weights).reduce((a, b) => a + b, 0).toFixed(2)}</div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <NumField label="Profit reference $" hint="profit that scores 1.0" value={draft.ranking.profit_reference_usd} onChange={(v) => upd("ranking", { ...draft.ranking, profit_reference_usd: v ?? 100 })} />
            <NumField label="ROI reference %" value={draft.ranking.roi_reference_pct} onChange={(v) => upd("ranking", { ...draft.ranking, roi_reference_pct: v ?? 100 })} />
          </div>
          <div className="label mt-3">Feedback adjustments (added to score fraction)</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {Object.entries(draft.ranking.feedback_adjustments).map(([k, v]) => (
              <label key={k} className="flex items-center justify-between gap-2 text-xs"><span>{titleCase(k)}</span><input className="input num w-20 py-0.5 text-right" type="number" step="0.05" min="-1" max="1" value={v} onChange={(e) => upd("ranking", { ...draft.ranking, feedback_adjustments: { ...draft.ranking.feedback_adjustments, [k]: Number(e.target.value) } })} /></label>
            ))}
          </div>
        </Card>

        <Card title="Analysis pipeline">
          <div className="grid grid-cols-3 gap-2">
            <NumField label="Auto-escalate min triage interest" value={draft.analysis.auto_escalate_min_triage_interest} onChange={(v) => upd("analysis", { ...draft.analysis, auto_escalate_min_triage_interest: v ?? 55 })} />
            <NumField label="Min current bid" value={draft.analysis.min_current_bid} onChange={(v) => upd("analysis", { ...draft.analysis, min_current_bid: v ?? 0 })} />
            <NumField label="Max current bid" value={draft.analysis.max_current_bid} onChange={(v) => upd("analysis", { ...draft.analysis, max_current_bid: v ?? 500 })} />
          </div>
          <Field label="Exclude keywords (prefilter rejects)" className="mt-2" hint="comma separated"><textarea className="input" rows={2} value={draft.analysis.exclude_keywords.join(", ")} onChange={(e) => upd("analysis", { ...draft.analysis, exclude_keywords: splitList(e.target.value) })} /></Field>
          <Field label="Boost keywords (prefilter interest)" className="mt-2" hint="comma separated"><textarea className="input" rows={4} value={draft.analysis.boost_keywords.join(", ")} onChange={(e) => upd("analysis", { ...draft.analysis, boost_keywords: splitList(e.target.value) })} /></Field>
        </Card>

        <div className="flex flex-col gap-3">
          <Card title="Notifications">
            <div className="grid grid-cols-2 gap-2">
              <NumField label="Default reminder (min before end)" value={draft.notifications.reminder_minutes_before_end} onChange={(v) => upd("notifications", { ...draft.notifications, reminder_minutes_before_end: v ?? 30 })} />
              <label className="flex items-center gap-2 self-end pb-2 text-sm"><input type="checkbox" checked={draft.notifications.enable_console_reminders} onChange={(e) => upd("notifications", { ...draft.notifications, enable_console_reminders: e.target.checked })} /> Console reminders</label>
            </div>
          </Card>
          <Card title="Model pricing (USD per 1M tokens: input, output)" bodyClass="p-0">
            <table className="tbl">
              <thead><tr><th>Model</th><th className="r">Input</th><th className="r">Output</th></tr></thead>
              <tbody>{Object.entries(draft.model_pricing_usd_per_1m).map(([m, [i, o]]) => (
                <tr key={m}><td className="num">{m}</td>
                  <td className="r"><input className="input num w-20 py-0.5 text-right" type="number" step="0.01" min="0" value={i} onChange={(e) => upd("model_pricing_usd_per_1m", { ...draft.model_pricing_usd_per_1m, [m]: [Number(e.target.value), o] })} /></td>
                  <td className="r"><input className="input num w-20 py-0.5 text-right" type="number" step="0.01" min="0" value={o} onChange={(e) => upd("model_pricing_usd_per_1m", { ...draft.model_pricing_usd_per_1m, [m]: [i, Number(e.target.value)] })} /></td>
                </tr>
              ))}</tbody>
            </table>
          </Card>
        </div>
      </div>
    </div>
  );
}

function splitList(s: string) { return s.split(",").map((x) => x.trim()).filter(Boolean); }

function NumField({ label, value, onChange, nullable, hint }: { label: string; value: number | null; onChange: (v: number | null) => void; nullable?: boolean; hint?: string }) {
  return (
    <Field label={label} hint={hint}>
      <input className="input" type="number" step="0.01" value={value ?? ""} placeholder={nullable ? "unknown" : undefined} onChange={(e) => { const v = e.target.value; onChange(v === "" ? (nullable ? null : 0) : Number(v)); }} />
    </Field>
  );
}
