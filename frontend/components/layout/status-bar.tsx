"use client";
import { RefreshCw, WifiOff } from "lucide-react";
import type { ApiError } from "@/lib/api";
import type { StatusResponse } from "@/lib/types";
import { titleCase } from "@/lib/format";

const ORDER = ["ai_triage", "ai_deep", "demo_mode", "ingest_manual", "ingest_email", "sold_data_manual", "sold_data_ebay_insights", "active_data_ebay_browse", "webhooks", "worker", "ingest_sgw_unofficial"];
const SHORT: Record<string, string> = {
  ai_triage: "AI triage", ai_deep: "AI deep", demo_mode: "Demo", ingest_manual: "Manual ingest", ingest_email: "E-mail ingest",
  sold_data_manual: "Comps manual", sold_data_ebay_insights: "eBay sold", active_data_ebay_browse: "eBay active", webhooks: "Webhooks", worker: "Worker", ingest_sgw_unofficial: "SGW API",
};

function dot(state: string) {
  switch (state) {
    case "live": return "bg-green";
    case "available": case "demo": return "bg-demo";
    case "needs_config": return "bg-amber";
    case "disabled": return "bg-gray";
    default: return "bg-gray";
  }
}

export function StatusBar({ status, error, loading, onRefresh }: { status?: StatusResponse; error: ApiError | null; loading: boolean; onRefresh: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex min-h-[38px] items-center gap-2 border-b border-border bg-elev/95 px-4 backdrop-blur">
      <div className="scrollbar-thin flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto py-1.5">
        {error && (
          <span className="inline-flex items-center gap-1.5 rounded border border-red/40 bg-red/10 px-2 py-0.5 text-xs text-red">
            <WifiOff size={12} /> Backend unreachable: {error.message}
          </span>
        )}
        {!error && loading && !status && <span className="text-xs text-dim">Loading system status…</span>}
        {status && ORDER.filter((k) => status.components[k]).map((k) => {
          const c = status.components[k];
          return (
            <span key={k} title={`${titleCase(k)}: ${c.state}\n${c.detail}`} className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-border bg-elev-2 px-1.5 py-0.5 text-[11px] text-muted">
              <span className={`h-1.5 w-1.5 rounded-full ${dot(c.state)}`} />
              {SHORT[k] || titleCase(k)}
              {c.state !== "live" && <span className="text-dim">{c.state === "needs_config" ? "config" : c.state === "available" ? "on" : c.state}</span>}
            </span>
          );
        })}
      </div>
      {status && (
        <span className="num hidden shrink-0 text-[11px] text-dim lg:inline" title="Daily AI budget">
          budget ${status.budget.daily_budget_usd.toFixed(2)}/day
        </span>
      )}
      <button onClick={onRefresh} className="btn btn-ghost btn-xs shrink-0" title="Refresh status" aria-label="Refresh status"><RefreshCw size={12} /></button>
    </header>
  );
}
