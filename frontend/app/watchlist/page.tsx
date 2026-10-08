"use client";
import { Archive, BellRing, Bookmark, ExternalLink, RefreshCw, Save, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { countdown, fmtDate, money, num, numOrNull } from "@/lib/format";
import type { ListingSummary, WatchStatus } from "@/lib/types";
import { useApi, useNow } from "@/lib/useApi";
import { Countdown } from "@/components/listings/countdown";
import { Thumb } from "@/components/listings/thumb";
import { Badge, DemoBadge, TierBadge } from "@/components/ui/badges";
import { Alert, ApiErrorAlert, EmptyState, Skeleton, Spinner, Toggle } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

const STATUSES: WatchStatus[] = ["watching", "bidding", "won", "lost", "passed", "archived"];

export default function WatchlistPage() {
  const [includeArchived, setIncludeArchived] = useState(false);
  const list = useApi(() => api.watchlist(includeArchived), [includeArchived], { pollMs: 30000 });
  const due = useApi(() => api.dueReminders(), [], { pollMs: 30000 });
  const now = useNow(1000);
  const items = [...(list.data?.items ?? [])].sort((a, b) => countdown(a.ends_at, now).ms - countdown(b.ends_at, now).ms);
  const onChanged = (u: ListingSummary | null, id: number) => list.setData((prev) => prev ? { items: u ? prev.items.map((x) => x.id === id ? u : x) : prev.items.filter((x) => x.id !== id) } : prev);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Watchlist</h1>
          <p className="text-xs text-muted">{items.length} item{items.length === 1 ? "" : "s"}, ending soonest first. Reminders fire {`(remind_minutes_before_end)`} before the auction ends.</p>
        </div>
        <div className="flex items-center gap-2">
          <Toggle checked={includeArchived} onChange={setIncludeArchived} label="Show archived" />
          <button className="btn btn-sm" onClick={() => { list.refresh(); due.refresh(); }}><RefreshCw size={13} className={list.refreshing ? "animate-spin" : ""} /> Refresh</button>
        </div>
      </div>

      {due.data && due.data.due.length > 0 && (
        <Alert kind="warning" title={<span className="flex items-center gap-1.5"><BellRing size={13} /> {due.data.due.length} reminder{due.data.due.length === 1 ? "" : "s"} due now</span>}>
          <ul className="mt-1 space-y-0.5">
            {due.data.due.map((d) => (
              <li key={d.listing_id} className="flex flex-wrap items-center gap-2">
                <Link href={`/items/${d.listing_id}`} className="font-medium text-fg hover:underline">{d.title}</Link>
                <span className="num">ends in {num(d.minutes_left, 0)} min</span>
                <span className="num">bid {money(d.current_bid)}</span>
                <span className="num">your max {money(d.user_max_bid)}</span>
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {list.error && <ApiErrorAlert error={list.error} />}
      {list.loading && !list.data ? <Skeleton className="h-40" /> : items.length === 0 ? (
        <EmptyState icon={<Bookmark size={26} />} title="Nothing on the watchlist">Use the bookmark button on the <Link href="/" className="text-accent underline">dashboard</Link> or an item page to start watching auctions.</EmptyState>
      ) : (
        <div className="scrollbar-thin overflow-x-auto rounded-lg border border-border bg-elev">
          <table className="tbl w-full min-w-[1000px] table-fixed">
            <colgroup><col style={{ width: 48 }} /><col /><col style={{ width: 96 }} /><col style={{ width: 96 }} /><col style={{ width: 118 }} /><col style={{ width: 96 }} /><col style={{ width: 118 }} /><col style={{ width: 110 }} /><col style={{ width: 84 }} /></colgroup>
            <thead><tr><th></th><th>Listing</th><th>Ends</th><th className="r">Current bid</th><th className="r">Your max bid</th><th className="r">Rec. max</th><th>Status</th><th>Remind (min)</th><th></th></tr></thead>
            <tbody>{items.map((l) => <Row key={l.id} l={l} onChanged={onChanged} />)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Row({ l, onChanged }: { l: ListingSummary; onChanged: (u: ListingSummary | null, id: number) => void }) {
  const toast = useToast();
  const router = useRouter();
  const w = l.watchlist!;
  const [busy, setBusy] = useState<string | null>(null);
  const [maxBid, setMaxBid] = useState(w.user_max_bid?.toString() ?? "");
  const [remind, setRemind] = useState(w.remind_minutes_before_end?.toString() ?? "");
  const [price, setPrice] = useState("");
  const rec = l.opportunity?.finance?.max_bid ?? null;
  const userMax = numOrNull(maxBid);
  const dirty = userMax !== (w.user_max_bid ?? null) || (remind === "" ? null : Number(remind)) !== (w.remind_minutes_before_end ?? null);

  async function save(patch: Parameters<typeof api.putWatch>[1]) {
    setBusy("save");
    try { const u = await api.putWatch(l.id, patch); onChanged(u, l.id); toast.success("Watchlist updated"); }
    catch (e) { toast.apiError(e, "Watchlist update"); } finally { setBusy(null); }
  }
  async function remove() {
    setBusy("remove");
    try { await api.removeWatch(l.id); onChanged(null, l.id); toast.info("Removed from watchlist"); }
    catch (e) { toast.apiError(e, "Remove"); setBusy(null); }
  }
  async function updatePrice() {
    const p = numOrNull(price);
    if (p === null) return;
    setBusy("price");
    try {
      await api.snapshot(l.id, { current_bid: p });
      const fresh = await api.listings({ q: "", limit: 1, offset: 0, include_demo: true, include_archived: true, sort: "updated" });
      const u = fresh.items.find((x) => x.id === l.id);
      onChanged(u ? { ...u, watchlist: l.watchlist } : { ...l, current_bid: p }, l.id);
      setPrice("");
      toast.success("Price updated", "Snapshot recorded and opportunity recomputed.");
    } catch (e) { toast.apiError(e, "Price update"); } finally { setBusy(null); }
  }

  const curBid = l.current_bid ?? 0;
  const overUser = userMax != null && curBid > userMax;
  const overRec = rec != null && curBid > rec;
  return (
    <tr className={w.archived ? "opacity-60" : ""}>
      <td><Thumb image={l.thumbnail} alt={l.title} size={40} /></td>
      <td className="overflow-hidden">
        <div className="flex min-w-0 items-center gap-1.5">
          <Link href={`/items/${l.id}`} className="min-w-0 truncate font-medium hover:underline" title={l.title}>{l.title}</Link>
          {l.is_demo && <DemoBadge />}
          {l.source_url && <a href={l.source_url} target="_blank" rel="noopener noreferrer" className="text-dim hover:text-fg" title="Open auction"><ExternalLink size={12} /></a>}
        </div>
        <div className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-muted">
          <span className="min-w-0 truncate">{l.identification?.summary ?? "not identified"}</span>
          <TierBadge tier={l.opportunity?.tier} />
        </div>
        <div className="mt-1 flex items-center gap-1">
          <input className="input num w-24 py-0.5 text-xs" type="number" step="0.01" min="0" placeholder="new bid" value={price} onChange={(e) => setPrice(e.target.value)} aria-label="New current bid" />
          <button className="btn btn-xs" onClick={updatePrice} disabled={busy !== null || numOrNull(price) === null} title="Record a manual price snapshot">{busy === "price" ? <Spinner size={11} /> : "Update price"}</button>
          {l.status !== "active" && <Badge tone="gray">{l.status}</Badge>}
        </div>
      </td>
      <td><Countdown endsAt={l.ends_at} /><div className="text-[10px] text-dim">{fmtDate(l.ends_at)}</div></td>
      <td className={`r num ${overUser ? "text-red" : ""}`} title={overUser ? "Current bid is above your max" : ""}>{money(l.current_bid)}<div className="text-[10px] text-dim">{num(l.num_bids)} bids</div></td>
      <td className="r">
        <input className={`input num w-full py-0.5 text-right ${overUser ? "border-red" : ""}`} type="number" step="1" min="0" value={maxBid} onChange={(e) => setMaxBid(e.target.value)} aria-label="Your max bid" />
      </td>
      <td className={`r num ${overRec ? "text-red" : "text-blue"}`} title={overRec ? "Current bid exceeds recommended max" : "Recommended max bid"}>{money(rec)}{userMax != null && rec != null && userMax > rec && <div className="text-[10px] text-amber">yours is higher</div>}</td>
      <td>
        <select className="input py-0.5" value={w.status} disabled={busy !== null} onChange={(e) => save({ status: e.target.value as WatchStatus, archived: e.target.value === "archived" ? true : w.archived })} aria-label="Watch status">
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        {w.archived && <div className="text-[10px] text-dim">archived</div>}
      </td>
      <td><input className="input num w-full py-0.5" type="number" step="5" min="0" value={remind} onChange={(e) => setRemind(e.target.value)} aria-label="Remind minutes before end" /></td>
      <td>
        <div className="flex items-center justify-end gap-1">
          <button className={`btn btn-xs ${dirty ? "btn-primary" : ""}`} disabled={busy !== null || !dirty} onClick={() => save({ user_max_bid: userMax, remind_minutes_before_end: remind === "" ? null : Math.round(Number(remind)) })} title="Save max bid / reminder">{busy === "save" ? <Spinner size={11} /> : <Save size={12} />}</button>
          <button className="btn btn-xs" disabled={busy !== null} onClick={() => save({ archived: !w.archived, status: w.archived ? "watching" : "archived" })} title={w.archived ? "Unarchive" : "Archive"}><Archive size={12} /></button>
          <button className="btn btn-xs btn-danger" disabled={busy !== null} onClick={remove} title="Remove from watchlist"><Trash2 size={12} /></button>
          <button className="hidden" onClick={() => router.push(`/items/${l.id}`)} aria-hidden />
        </div>
      </td>
    </tr>
  );
}
