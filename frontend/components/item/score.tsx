"use client";
import { fmtDate, money, num, pct, titleCase } from "@/lib/format";
import type { ListingDetail } from "@/lib/types";
import { Badge, TierBadge, tierTone } from "@/components/ui/badges";
import { Bar, Card } from "@/components/ui/primitives";

export function ScoreBreakdown({ listing }: { listing: ListingDetail }) {
  const opp = listing.opportunity;
  const comp = opp?.components;
  const fin = opp?.finance;
  if (!opp || !comp) {
    return <Card title="Opportunity score"><p className="text-xs text-dim">Not scored yet. Run analysis and add comparables.</p></Card>;
  }
  const keys = Object.keys(comp.weights);
  const contributions = keys.map((k) => ({ k, v: comp.components[k] ?? 0, w: comp.weights[k] ?? 0, c: (comp.components[k] ?? 0) * (comp.weights[k] ?? 0) }));
  const maxC = Math.max(...contributions.map((x) => x.w), 0.01);
  const toneCls = { green: "text-green", amber: "text-amber", blue: "text-blue", gray: "text-muted", red: "text-red", purple: "text-purple", demo: "text-demo", accent: "text-accent" }[tierTone(comp.tier)];
  return (
    <Card title="Opportunity score" actions={<Badge tone="gray" title={comp.label}>{comp.label}</Badge>}>
      <div className="flex items-end gap-3">
        <div className={`num text-4xl font-bold leading-none ${toneCls}`}>{num(comp.score, 1)}</div>
        <div className="flex flex-col gap-1 pb-0.5">
          <TierBadge tier={comp.tier} />
          <span className="num text-[11px] text-dim">time factor {num(comp.time_factor, 2)} · {comp.hours_left != null ? `${num(comp.hours_left, 1)}h left` : "no end"} · feedback adj {comp.feedback_adjustment >= 0 ? "+" : ""}{num(comp.feedback_adjustment, 2)}</span>
        </div>
      </div>
      <table className="tbl mt-3">
        <thead><tr><th>Component</th><th className="r">Value</th><th className="r">Weight</th><th>Weighted</th></tr></thead>
        <tbody>
          {contributions.map((x) => (
            <tr key={x.k}>
              <td className="text-xs">{titleCase(x.k)}</td>
              <td className="r num text-xs">{num(x.v, 2)}</td>
              <td className="r num text-xs text-muted">{num(x.w, 2)}</td>
              <td className="w-[38%]"><Bar value={x.c} max={maxC} tone={x.v >= 0.7 ? "green" : x.v >= 0.4 ? "amber" : "red"} label={`${titleCase(x.k)}: ${num(x.v, 2)} × ${num(x.w, 2)} = ${num(x.c, 3)}`} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {fin && (
        <div className="num mt-3 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-muted">
          <span>Expected profit <span className={fin.expected_profit != null && fin.expected_profit >= 0 ? "text-green" : "text-red"}>{money(fin.expected_profit)}</span></span>
          <span>ROI {pct(fin.expected_roi_pct)}</span>
          <span>Max bid <span className={fin.over_max_bid ? "text-red" : "text-fg"}>{money(fin.max_bid)}</span></span>
          <span>Break-even {money(fin.break_even_bid)}</span>
          <span>Risk-adj. profit {money(fin.risk_adjusted_profit)}</span>
          <span>Platform {fin.platform}</span>
          {!fin.complete && <span className="col-span-2 text-amber">Finance incomplete: unknown {fin.unknown_costs.join(", ") || "costs"}</span>}
        </div>
      )}
      <div className="mt-2 text-[10.5px] text-dim">Scored {fmtDate(opp.computed_at)}. Weights are editable in Settings → ranking.</div>
    </Card>
  );
}
