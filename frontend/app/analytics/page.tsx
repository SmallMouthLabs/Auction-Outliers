"use client";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { money, num, pct, tierLabel, titleCase } from "@/lib/format";
import type { Tier } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { TierBadge, tierTone } from "@/components/ui/badges";
import { ApiErrorAlert, Bar, Card, Skeleton, Stat } from "@/components/ui/primitives";

const TIERS: Tier[] = ["HIGH_CONFIDENCE", "SPECULATIVE_HIGH_UPSIDE", "NEEDS_RESEARCH", "LOW_VALUE"];

export default function AnalyticsPage() {
  const a = useApi(() => api.analytics(), [], { pollMs: 60000 });
  const d = a.data;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Analytics</h1>
          <p className="text-xs text-muted">Pipeline throughput, projected vs realized economics, AI spend{d ? ` (last ${d.ai_usage.days} days)` : ""}.</p>
        </div>
        <button className="btn btn-sm" onClick={a.refresh}><RefreshCw size={13} className={a.refreshing ? "animate-spin" : ""} /> Refresh</button>
      </div>
      {a.error && <ApiErrorAlert error={a.error} />}
      {!d ? <div className="grid grid-cols-4 gap-2">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div> : (
        <>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
            <Stat label="Items" value={num(d.items_total)} sub={`${num(d.items_demo)} demo`} />
            <Stat label="Deep-analyzed" value={num(d.items_analyzed_deep)} sub={`${pct(d.items_total ? (d.items_analyzed_deep / d.items_total) * 100 : 0)} of items`} />
            <Stat label="Avg projected ROI" value={pct(d.avg_projected_roi_pct)} sub="opportunities w/ finance" />
            <Stat label="Avg projected profit" value={money(d.avg_projected_profit_usd)} />
            <Stat label="ID corrections" value={num(d.identification_corrections)} sub="user overrides of AI" />
            <Stat label="Purchases / sales" value={`${num(d.purchases)} / ${num(d.sales)}`} />
            <Stat label="Realized profit" value={money(d.realized_profit_total)} tone={d.realized_profit_total > 0 ? "green" : d.realized_profit_total < 0 ? "red" : undefined} />
            <Stat label="Avg days to sale" value={d.avg_days_to_sale != null ? num(d.avg_days_to_sale, 1) : "—"} />
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            <Card title="Opportunities by tier">
              <BarList rows={TIERS.map((t) => ({ label: tierLabel(t), value: d.opportunities_by_tier[t] ?? 0, tone: tierTone(t) as "green" | "amber" | "blue" | "gray" }))} />
              {Object.keys(d.by_domain).length > 0 && (
                <table className="tbl mt-3">
                  <thead><tr><th>Domain</th>{TIERS.map((t) => <th key={t} className="r" title={tierLabel(t)}>{tierLabel(t).split(" ")[0]}</th>)}</tr></thead>
                  <tbody>{Object.entries(d.by_domain).map(([dom, tiers]) => (
                    <tr key={dom}><td className="capitalize">{dom}</td>{TIERS.map((t) => <td key={t} className="r num">{tiers[t] ?? 0}</td>)}</tr>
                  ))}</tbody>
                </table>
              )}
            </Card>
            <Card title="Opportunity categories" actions={<span className="text-[10px] text-dim">non-low-value items</span>}>
              {Object.keys(d.opportunity_categories).length === 0 ? <p className="text-xs text-dim">No opportunities yet.</p> : (
                <BarList rows={Object.entries(d.opportunity_categories).sort((x, y) => y[1] - x[1]).map(([k, v]) => ({ label: k, value: v, tone: "accent" as const }))} />
              )}
            </Card>
            <Card title="Feedback counts">
              {Object.keys(d.feedback_counts).length === 0 ? <p className="text-xs text-dim">No feedback recorded yet.</p> : (
                <BarList rows={Object.entries(d.feedback_counts).sort((x, y) => y[1] - x[1]).map(([k, v]) => ({ label: titleCase(k), value: v, tone: (k === "excellent_find" ? "green" : k.startsWith("incorrect") || k === "too_risky" || k === "not_worth_buying" ? "red" : "amber") as "green" | "red" | "amber" }))} />
              )}
            </Card>
          </div>

          <Card title="AI usage & cost" actions={<span className="num text-xs text-muted">{num(d.recent_runs)} runs in {d.ai_usage.days} days</span>}>
            <div className="mb-3">
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-muted">Spent today vs daily budget</span>
                <span className="num">{money(d.ai_usage.spent_today_usd)} / {money(d.ai_usage.daily_budget_usd)} ({pct(d.ai_usage.daily_budget_usd ? (d.ai_usage.spent_today_usd / d.ai_usage.daily_budget_usd) * 100 : 0)})</span>
              </div>
              <Bar value={d.ai_usage.spent_today_usd} max={d.ai_usage.daily_budget_usd || 1} tone={d.ai_usage.spent_today_usd / (d.ai_usage.daily_budget_usd || 1) > 0.8 ? "red" : d.ai_usage.spent_today_usd / (d.ai_usage.daily_budget_usd || 1) > 0.5 ? "amber" : "green"} className="h-2.5" label="Daily budget used" />
            </div>
            {d.ai_usage.by_model.length === 0 ? <p className="text-xs text-dim">No paid provider calls recorded (demo provider calls are free and not logged).</p> : (
              <div className="scrollbar-thin overflow-x-auto">
                <table className="tbl">
                  <thead><tr><th>Provider</th><th>Model</th><th>Stage</th><th className="r">Calls</th><th className="r">Errors</th><th className="r">Tokens in</th><th className="r">Tokens out</th><th className="r">Est. cost</th><th className="r">Avg ms</th></tr></thead>
                  <tbody>{d.ai_usage.by_model.map((r, i) => (
                    <tr key={i}><td>{r.provider}</td><td className="num">{r.model}</td><td>{r.stage}</td><td className="r num">{num(r.calls)}</td><td className={`r num ${r.errors ? "text-red" : ""}`}>{num(r.errors)}</td><td className="r num">{num(r.tokens_in)}</td><td className="r num">{num(r.tokens_out)}</td><td className="r num">${r.est_cost_usd.toFixed(4)}</td><td className="r num">{num(r.avg_duration_ms)}</td></tr>
                  ))}</tbody>
                  <tfoot><tr className="font-semibold"><td colSpan={3}>Total</td><td className="r num">{num(d.ai_usage.by_model.reduce((s, r) => s + r.calls, 0))}</td><td className="r num">{num(d.ai_usage.by_model.reduce((s, r) => s + r.errors, 0))}</td><td className="r num">{num(d.ai_usage.by_model.reduce((s, r) => s + r.tokens_in, 0))}</td><td className="r num">{num(d.ai_usage.by_model.reduce((s, r) => s + r.tokens_out, 0))}</td><td className="r num">${d.ai_usage.by_model.reduce((s, r) => s + r.est_cost_usd, 0).toFixed(4)}</td><td></td></tr></tfoot>
                </table>
              </div>
            )}
          </Card>
          <div className="hidden"><TierBadge tier="LOW_VALUE" /></div>
        </>
      )}
    </div>
  );
}

function BarList({ rows }: { rows: { label: string; value: number; tone: "green" | "amber" | "blue" | "gray" | "red" | "accent" }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="flex flex-col gap-1.5">
      {rows.map((r) => (
        <div key={r.label} className="grid grid-cols-[minmax(0,1fr)_2.5rem] items-center gap-2">
          <div>
            <div className="mb-0.5 truncate text-xs" title={r.label}>{r.label}</div>
            <Bar value={r.value} max={max} tone={r.tone} label={`${r.label}: ${r.value}`} />
          </div>
          <div className="num text-right text-sm">{num(r.value)}</div>
        </div>
      ))}
    </div>
  );
}
