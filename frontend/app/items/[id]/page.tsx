"use client";
import { Archive, ArrowLeft, Bookmark, BookmarkCheck, ExternalLink, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, num, pct } from "@/lib/format";
import type { ListingDetail } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { Countdown } from "@/components/listings/countdown";
import { AuctionInfo } from "@/components/item/auction-info";
import { ComparablesPanel } from "@/components/item/comparables";
import { FinancePanel } from "@/components/item/finance";
import { Gallery } from "@/components/item/gallery";
import { Identification } from "@/components/item/identification";
import { ScoreBreakdown } from "@/components/item/score";
import { FeedbackPanel, NotesPanel, OutcomePanel, WatchlistControls } from "@/components/item/workspace";
import { Badge, DemoBadge, EvidenceBadge, MisidSignal, OriginBadge, StatusBadge, TierBadge } from "@/components/ui/badges";
import { Alert, ApiErrorAlert, Skeleton, Stat, Tabs } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

type Tab = "identification" | "comps" | "finance" | "auction" | "research";
const TABS: { id: Tab; label: string }[] = [
  { id: "identification", label: "AI identification" },
  { id: "comps", label: "Comparables & valuation" },
  { id: "finance", label: "Finance" },
  { id: "auction", label: "Auction data" },
  { id: "research", label: "Research & outcome" },
];

export default function ItemPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const router = useRouter();
  const toast = useToast();
  const listing = useApi(() => api.listing(id), [id], { enabled: Number.isFinite(id) });
  const settings = useApi(() => api.settings(), []);
  const providers = useApi(() => api.soldDataProviders(), []);
  const [tab, setTab] = useState<Tab>("identification");
  const [imgIndex, setImgIndex] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    const h = window.location.hash.replace("#", "") as Tab;
    if (TABS.some((t) => t.id === h)) setTab(h);
  }, []);
  const changeTab = (t: Tab) => { setTab(t); history.replaceState(null, "", `#${t}`); };

  const onUpdate = useCallback((d: ListingDetail) => listing.setData(d), [listing]);
  const reload = useCallback(async () => { await listing.refresh(); }, [listing]);
  const focusImage = (i: number) => { setImgIndex(i); document.getElementById("gallery")?.scrollIntoView({ behavior: "smooth", block: "nearest" }); };

  const l = listing.data;

  async function toggleWatch() {
    if (!l) return;
    setBusy("watch");
    try {
      if (l.watchlist && !l.watchlist.archived) { await api.removeWatch(l.id); onUpdate({ ...l, watchlist: null }); toast.info("Removed from watchlist"); }
      else { const u = await api.putWatch(l.id, { status: "watching" }); onUpdate({ ...l, watchlist: u.watchlist }); toast.success("Added to watchlist"); }
    } catch (e) { toast.apiError(e, "Watchlist"); } finally { setBusy(null); }
  }
  async function archive() {
    if (!l) return;
    setBusy("archive");
    try { onUpdate(await api.patchListing(l.id, { archived: !l.archived })); toast.success(l.archived ? "Unarchived" : "Archived"); }
    catch (e) { toast.apiError(e, "Archive"); } finally { setBusy(null); }
  }
  async function del() {
    if (!l || !confirm(`Permanently delete "${l.title}" and all its analysis?`)) return;
    setBusy("delete");
    try { await api.deleteListing(l.id); toast.info("Listing deleted"); router.push("/"); }
    catch (e) { toast.apiError(e, "Delete"); setBusy(null); }
  }

  if (listing.error && !l) {
    return (
      <div className="flex flex-col gap-3">
        <Link href="/" className="btn btn-sm w-fit"><ArrowLeft size={13} /> Back</Link>
        <ApiErrorAlert error={listing.error} />
      </div>
    );
  }
  if (!l) {
    return <div className="grid gap-3 lg:grid-cols-[420px_1fr]"><Skeleton className="aspect-[4/3]" /><div className="flex flex-col gap-2"><Skeleton className="h-8" /><Skeleton className="h-24" /><Skeleton className="h-40" /></div></div>;
  }

  const fin = l.opportunity?.finance;
  const ident = l.identification;
  const val = l.valuation;
  const watching = !!l.watchlist && !l.watchlist.archived;
  const platformKeys = Object.keys(settings.data?.settings.platforms ?? {});

  return (
    <div className="flex flex-col gap-3">
      {/* header */}
      <div className="flex flex-wrap items-start gap-2">
        <Link href="/" className="btn btn-sm" title="Back to dashboard"><ArrowLeft size={13} /></Link>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <h1 className="text-lg font-semibold leading-tight">{l.title}</h1>
            {l.is_demo && <DemoBadge />}
            <StatusBadge status={l.status} />
            {l.archived && <Badge tone="gray">archived</Badge>}
            <span className="num text-xs text-dim">#{l.id} · {l.source}{l.source_item_id ? ` · ${l.source_item_id}` : ""}</span>
          </div>
          {ident && (
            <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-sm text-muted">
              <span>{ident.summary}</span>
              <span className="num text-dim">{ident.confidence != null ? `${Math.round(ident.confidence * 100)}%` : ""}</span>
              <OriginBadge origin={ident.origin} />
              <MisidSignal value={ident.misidentification_signal} />
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button className="btn btn-sm" onClick={reload} disabled={listing.refreshing} title="Reload"><RefreshCw size={13} className={listing.refreshing ? "animate-spin" : ""} /></button>
          {l.source_url && <a className="btn btn-sm" href={l.source_url} target="_blank" rel="noopener noreferrer"><ExternalLink size={13} /> Auction page</a>}
          <button className={`btn btn-sm ${watching ? "text-accent" : ""}`} onClick={toggleWatch} disabled={busy !== null}>{watching ? <BookmarkCheck size={13} /> : <Bookmark size={13} />} {watching ? "Watching" : "Watch"}</button>
          <button className="btn btn-sm" onClick={archive} disabled={busy !== null} title={l.archived ? "Unarchive" : "Archive"}><Archive size={13} /></button>
          <button className="btn btn-sm btn-danger" onClick={del} disabled={busy !== null} title="Delete listing"><Trash2 size={13} /></button>
        </div>
      </div>

      {/* top: gallery + metrics */}
      <div className="grid gap-3 lg:grid-cols-[minmax(320px,440px)_1fr]">
        <div id="gallery">
          <Gallery listingId={l.id} images={l.images} index={imgIndex} onIndex={setImgIndex} onChanged={reload} />
        </div>
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-1.5 md:grid-cols-3 2xl:grid-cols-6">
            <Stat label="Current bid" value={money(l.current_bid)} sub={`${num(l.num_bids)} bids · ship ${money(l.shipping_cost)}`} />
            <Stat label="Ends" value={<Countdown endsAt={l.ends_at} showIcon={false} />} sub={l.ends_at ? new Date(l.ends_at.endsWith("Z") ? l.ends_at : `${l.ends_at}Z`).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "no end time"} />
            <Stat label="Est. resale" value={val && val.expected != null ? `${money(val.conservative, { cents: false })}–${money(val.optimistic, { cents: false })}` : "—"} sub={<EvidenceBadge quality={val?.evidence_quality} speculative={val?.is_speculative} />} />
            <Stat label="Expected profit" value={money(fin?.expected_profit)} tone={fin?.expected_profit != null ? (fin.expected_profit >= 0 ? "green" : "red") : "muted"} sub={fin?.expected_roi_pct != null ? `${pct(fin.expected_roi_pct)} ROI · risk-adj ${money(fin.risk_adjusted_profit)}` : "no finance"} />
            <Stat label="Max bid" value={money(fin?.max_bid)} tone={fin?.over_max_bid ? "red" : "blue"} sub={fin?.over_max_bid ? <span className="text-red">current bid exceeds max</span> : fin ? `break-even ${money(fin.break_even_bid)}` : ""} />
            <Stat label="Score" value={l.opportunity?.score != null ? num(l.opportunity.score, 1) : "—"} sub={<TierBadge tier={l.opportunity?.tier} />} />
          </div>
          {fin && !fin.complete && (
            <Alert kind="warning" title="Finance incomplete">Unknown costs: {fin.unknown_costs.map((c) => c.replace(/_/g, " ")).join(", ") || "see Finance tab"}. Max bid and profit are not reliable until they are set.</Alert>
          )}
          <div className="grid gap-3 md:grid-cols-2">
            <ScoreBreakdown listing={l} />
            <div className="flex flex-col gap-3">
              <WatchlistControls listing={l} onUpdate={onUpdate} />
              <FeedbackPanel listing={l} labels={settings.data?.feedback_labels ?? []} onUpdate={onUpdate} />
            </div>
          </div>
        </div>
      </div>

      <Tabs tabs={TABS.map((t) => ({ ...t, count: t.id === "comps" ? l.comparables.length : t.id === "research" ? l.notes.length + l.feedback.length : undefined }))} value={tab} onChange={changeTab} />

      {tab === "identification" && <Identification listing={l} onUpdate={onUpdate} onFocusImage={focusImage} />}
      {tab === "comps" && <ComparablesPanel listing={l} onUpdate={onUpdate} providers={providers.data?.providers ?? []} />}
      {tab === "finance" && <FinancePanel listing={l} settings={settings.data?.settings} />}
      {tab === "auction" && <AuctionInfo listing={l} onUpdate={onUpdate} />}
      {tab === "research" && (
        <div className="grid gap-3 lg:grid-cols-2">
          <NotesPanel listing={l} onUpdate={onUpdate} />
          <OutcomePanel listing={l} onUpdate={onUpdate} platforms={platformKeys} />
        </div>
      )}
    </div>
  );
}
