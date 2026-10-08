"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, Bookmark, BookmarkCheck, ExternalLink, Search } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { conf, money, num, pct } from "@/lib/format";
import type { ListingSummary } from "@/lib/types";
import { Badge, DemoBadge, EvidenceBadge, MisidSignal, OriginBadge, TierBadge } from "@/components/ui/badges";
import { useToast } from "@/components/ui/toast";
import { Countdown } from "./countdown";
import { Thumb } from "./thumb";

export type SortKey = "score" | "profit" | "max_bid" | "ends_at" | "current_bid" | "confidence" | "updated";

const COLS: { key: string; label: string; sort?: SortKey; align?: "r"; title?: string }[] = [
  { key: "thumb", label: "" },
  { key: "title", label: "Listing / AI identification" },
  { key: "bid", label: "Bid", sort: "current_bid", align: "r", title: "Current bid (bids)" },
  { key: "resale", label: "Est. resale", align: "r", title: "Valuation: conservative - optimistic" },
  { key: "profit", label: "Exp. profit", sort: "profit", align: "r" },
  { key: "max_bid", label: "Max bid", sort: "max_bid", align: "r", title: "Max recommended bid (red = current bid already exceeds it)" },
  { key: "score", label: "Score", sort: "score", align: "r" },
  { key: "misid", label: "Misid", title: "Misidentification signal" },
  { key: "ends", label: "Ends", sort: "ends_at" },
  { key: "actions", label: "" },
];

export function ListingTable({ items, sort, order, onSort, onChanged, compact = false }: {
  items: ListingSummary[];
  sort?: SortKey;
  order?: "asc" | "desc";
  onSort?: (s: SortKey) => void;
  onChanged?: (updated: ListingSummary) => void;
  compact?: boolean;
}) {
  const router = useRouter();
  return (
    <div className="scrollbar-thin overflow-x-auto rounded-lg border border-border bg-elev">
      <table className="tbl w-full min-w-[960px] table-fixed">
        <colgroup>
          <col style={{ width: 52 }} />
          <col />
          <col style={{ width: 104 }} />
          <col style={{ width: 118 }} />
          <col style={{ width: 92 }} />
          <col style={{ width: 80 }} />
          <col style={{ width: 118 }} />
          <col style={{ width: 54 }} />
          <col style={{ width: 86 }} />
          <col style={{ width: 66 }} />
        </colgroup>
        <thead>
          <tr>
            {COLS.map((c) => (
              <th key={c.key} className={c.align === "r" ? "r" : ""} title={c.title}>
                {c.sort && onSort ? (
                  <button className="inline-flex items-center gap-1 uppercase hover:text-fg" onClick={() => onSort(c.sort!)}>
                    {c.label}
                    {sort === c.sort && (order === "asc" ? <ArrowUp size={11} /> : <ArrowDown size={11} />)}
                  </button>
                ) : c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((l) => (
            <Row key={l.id} l={l} compact={compact} onChanged={onChanged} onOpen={() => router.push(`/items/${l.id}`)} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({ l, compact, onChanged, onOpen }: { l: ListingSummary; compact: boolean; onChanged?: (u: ListingSummary) => void; onOpen: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const fin = l.opportunity?.finance;
  const val = l.valuation;
  const ident = l.identification;
  const watching = !!l.watchlist && !l.watchlist.archived;

  async function toggleWatch(e: React.MouseEvent) {
    e.stopPropagation();
    setBusy(true);
    try {
      if (watching) {
        await api.removeWatch(l.id);
        onChanged?.({ ...l, watchlist: null });
        toast.info("Removed from watchlist");
      } else {
        const u = await api.putWatch(l.id, { status: "watching" });
        onChanged?.(u);
        toast.success("Added to watchlist");
      }
    } catch (err) {
      toast.apiError(err, "Watchlist update");
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr
      tabIndex={0}
      className="cursor-pointer"
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === "Enter") onOpen(); }}
      aria-label={`Open ${l.title}`}
    >
      <td><Thumb image={l.thumbnail} alt={l.title} size={compact ? 36 : 44} /></td>
      <td className="overflow-hidden">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="min-w-0 truncate font-medium" title={l.title}>{l.title}</span>
          {l.is_demo && <DemoBadge />}
          {l.archived && <Badge tone="gray">archived</Badge>}
        </div>
        <div className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-muted">
          {ident ? (
            <>
              <span className="min-w-0 truncate" title={ident.summary}>{ident.summary}</span>
              <span className="num shrink-0 text-dim">{conf(ident.confidence)}</span>
              <OriginBadge origin={ident.origin} />
              {ident.warrants_research && <Search size={11} className="shrink-0 text-blue" aria-label="Warrants research" />}
            </>
          ) : (
            <span className="text-dim">Not identified yet</span>
          )}
        </div>
        {!compact && (
          <div className="mt-0.5 flex min-w-0 items-center gap-1.5 text-[11px] text-dim">
            <span className="capitalize">{l.domain || "unknown"}</span>
            {l.category && <span className="min-w-0 truncate" title={l.category}>· {l.category}</span>}
            <span>· {l.source}</span>
          </div>
        )}
      </td>
      <td className="r num whitespace-nowrap">
        <div>{money(l.current_bid)}</div>
        <div className="text-[11px] text-dim">{num(l.num_bids)} bid{l.num_bids === 1 ? "" : "s"}{l.shipping_cost != null ? ` · ship ${money(l.shipping_cost)}` : ""}</div>
      </td>
      <td className="r whitespace-nowrap">
        {val && val.expected != null ? (
          <>
            <div className="num">{money(val.conservative, { cents: false })}–{money(val.optimistic, { cents: false })}</div>
            <div className="mt-0.5 flex flex-col items-end gap-0.5"><EvidenceBadge quality={val.evidence_quality} speculative={val.is_speculative} className="flex-col items-end" /></div>
          </>
        ) : (
          <Badge tone="gray" title="No valuation - add sold comparables">Unsupported</Badge>
        )}
      </td>
      <td className={`r num whitespace-nowrap ${fin && fin.expected_profit != null ? (fin.expected_profit >= 0 ? "text-green" : "text-red") : "text-dim"}`}>
        <div>{money(fin?.expected_profit)}</div>
        <div className="text-[11px] text-dim">{fin?.expected_roi_pct != null ? `${pct(fin.expected_roi_pct)} ROI` : ""}{fin && !fin.complete ? " · incomplete" : ""}</div>
      </td>
      <td className="r whitespace-nowrap">
        {fin && fin.max_bid != null ? (
          <span className={`num rounded px-1.5 py-0.5 ${fin.over_max_bid ? "bg-red/20 font-semibold text-red" : ""}`} title={fin.over_max_bid ? "Current bid exceeds the maximum recommended bid" : "Max recommended bid"}>
            {money(fin.max_bid)}
          </span>
        ) : <span className="text-dim">—</span>}
      </td>
      <td className="r whitespace-nowrap">
        <div className="num text-base font-semibold">{l.opportunity?.score != null ? l.opportunity.score.toFixed(1) : "—"}</div>
        <TierBadge tier={l.opportunity?.tier} />
      </td>
      <td><MisidSignal value={ident?.misidentification_signal} /></td>
      <td className="whitespace-nowrap">
        <Countdown endsAt={l.ends_at} />
        {l.status !== "active" && <div className="text-[11px] text-dim">{l.status}</div>}
      </td>
      <td className="whitespace-nowrap">
        <div className="flex items-center justify-end gap-1">
          <button
            onClick={toggleWatch}
            disabled={busy}
            className={`btn btn-xs ${watching ? "text-accent" : ""}`}
            title={watching ? "Remove from watchlist" : "Watch this listing"}
            aria-label={watching ? "Unwatch" : "Watch"}
          >
            {watching ? <BookmarkCheck size={13} /> : <Bookmark size={13} />}
          </button>
          {l.source_url ? (
            <Link href={l.source_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="btn btn-xs" title="Open auction page in new tab" aria-label="Open auction">
              <ExternalLink size={13} />
            </Link>
          ) : (
            <span className="btn btn-xs opacity-40" title="No source URL"><ExternalLink size={13} /></span>
          )}
        </div>
      </td>
    </tr>
  );
}
