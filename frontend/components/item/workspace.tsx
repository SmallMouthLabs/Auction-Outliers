"use client";
import { Bookmark, BookmarkX, CheckCircle2, Flag, FlagOff, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, fromLocalInputValue, money, num, numOrNull, relTime, titleCase, toLocalInputValue } from "@/lib/format";
import type { ListingDetail, OutcomeIn, WatchStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badges";
import { Card, Field, Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

const WATCH_STATUSES: WatchStatus[] = ["watching", "bidding", "won", "lost", "passed", "archived"];

const FEEDBACK_TONE: Record<string, "green" | "amber" | "red" | "blue" | "gray" | "purple"> = {
  excellent_find: "green", worth_investigating: "blue", not_worth_buying: "red", incorrect_identification: "amber", incorrect_valuation: "amber",
  too_risky: "red", too_slow_to_resell: "amber", purchased: "purple", sold: "purple",
};

export function WatchlistControls({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const w = listing.watchlist;
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ status: (w?.status ?? "watching") as WatchStatus, user_max_bid: w?.user_max_bid?.toString() ?? "", remind: w?.remind_minutes_before_end?.toString() ?? "", notes: w?.notes ?? "" });
  const rec = listing.opportunity?.finance?.max_bid;
  async function save() {
    setBusy(true);
    try {
      const u = await api.putWatch(listing.id, { status: f.status, user_max_bid: numOrNull(f.user_max_bid), remind_minutes_before_end: f.remind === "" ? null : Math.round(Number(f.remind)), notes: f.notes || null, archived: f.status === "archived" });
      onUpdate({ ...listing, watchlist: u.watchlist });
      toast.success(w ? "Watchlist updated" : "Added to watchlist");
    } catch (e) { toast.apiError(e, "Watchlist"); } finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true);
    try { await api.removeWatch(listing.id); onUpdate({ ...listing, watchlist: null }); toast.info("Removed from watchlist"); }
    catch (e) { toast.apiError(e, "Remove from watchlist"); } finally { setBusy(false); }
  }
  const userOver = numOrNull(f.user_max_bid) != null && rec != null && numOrNull(f.user_max_bid)! > rec;
  return (
    <Card title="Watchlist" actions={w ? <Badge tone={w.status === "won" ? "green" : w.status === "lost" || w.status === "passed" ? "gray" : "accent"}>{w.status}{w.archived ? " · archived" : ""}</Badge> : <Badge tone="gray">not watched</Badge>}>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Status"><select className="input" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value as WatchStatus })}>{WATCH_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}</select></Field>
        <Field label="Your max bid" hint={rec != null ? <span>recommended {money(rec)}{userOver && <span className="text-red"> · above recommended</span>}</span> : undefined}><input className="input" type="number" step="1" min="0" value={f.user_max_bid} onChange={(e) => setF({ ...f, user_max_bid: e.target.value })} /></Field>
        <Field label="Remind (min before end)"><input className="input" type="number" step="5" min="0" value={f.remind} onChange={(e) => setF({ ...f, remind: e.target.value })} placeholder="settings default" /></Field>
        <Field label="Notes"><input className="input" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-[11px] text-dim">{w?.reminder_sent_at ? `Reminder sent ${relTime(w.reminder_sent_at)}` : w ? `Watching since ${relTime(w.created_at)}` : ""}</span>
        <div className="flex gap-1.5">
          {w && <button className="btn btn-sm btn-danger" onClick={remove} disabled={busy}><BookmarkX size={13} /> Remove</button>}
          <button className="btn btn-sm btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : <Bookmark size={13} />} {w ? "Save" : "Watch"}</button>
        </div>
      </div>
    </Card>
  );
}

export function FeedbackPanel({ listing, labels, onUpdate }: { listing: ListingDetail; labels: string[]; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | number | null>(null);
  async function add(label: string) {
    setBusy(label);
    try { const d = await api.addFeedback(listing.id, label, note || undefined); onUpdate(d); setNote(""); toast.success(`Feedback: ${titleCase(label)}`, "Score adjusted."); }
    catch (e) { toast.apiError(e, "Add feedback"); } finally { setBusy(null); }
  }
  async function del(id: number) {
    setBusy(id);
    try { const d = await api.deleteFeedback(listing.id, id); onUpdate(d); }
    catch (e) { toast.apiError(e, "Delete feedback"); } finally { setBusy(null); }
  }
  return (
    <Card title="Feedback" actions={<span className="text-[10px] text-dim">trains the ranking heuristics</span>}>
      <div className="flex flex-wrap gap-1.5">
        {labels.map((l) => (
          <button key={l} className={`btn btn-xs ${listing.feedback_labels.includes(l) ? "border-accent text-accent" : ""}`} onClick={() => add(l)} disabled={busy !== null} title={`Record "${titleCase(l)}"`}>
            {busy === l ? <Spinner size={11} /> : null} {titleCase(l)}
          </button>
        ))}
      </div>
      <input className="input mt-2" placeholder="Optional note attached to the next feedback click" value={note} onChange={(e) => setNote(e.target.value)} />
      {listing.feedback.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs">
          {listing.feedback.map((f) => (
            <li key={f.id} className="flex items-center gap-2">
              <Badge tone={FEEDBACK_TONE[f.label] ?? "gray"}>{titleCase(f.label)}</Badge>
              <span className="min-w-0 flex-1 truncate text-muted">{f.note}</span>
              <span className="num text-dim" title={fmtDate(f.created_at)}>{relTime(f.created_at)}</span>
              <button className="btn btn-ghost btn-xs text-dim hover:text-red" onClick={() => del(f.id)} disabled={busy !== null} aria-label="Delete feedback"><Trash2 size={11} /></button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function NotesPanel({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const [text, setText] = useState("");
  const [flagged, setFlagged] = useState(false);
  const [busy, setBusy] = useState<number | "add" | null>(null);
  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy("add");
    try { const d = await api.addNote(listing.id, text.trim(), flagged); onUpdate(d); setText(""); setFlagged(false); }
    catch (err) { toast.apiError(err, "Add note"); } finally { setBusy(null); }
  }
  async function patch(id: number, body: { flagged?: boolean; resolved?: boolean }) {
    setBusy(id);
    try { const d = await api.patchNote(listing.id, id, body); onUpdate(d); }
    catch (err) { toast.apiError(err, "Update note"); } finally { setBusy(null); }
  }
  const openFlags = listing.notes.filter((n) => n.flagged && !n.resolved).length;
  return (
    <Card title="Research notes" actions={openFlags > 0 ? <Badge tone="amber"><Flag size={10} /> {openFlags} open</Badge> : null}>
      <form onSubmit={add} className="flex flex-col gap-1.5">
        <textarea className="input" rows={2} placeholder="What to verify, who to ask, what you found…" value={text} onChange={(e) => setText(e.target.value)} />
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={flagged} onChange={(e) => setFlagged(e.target.checked)} /> Flag for investigation</label>
          <button className="btn btn-sm" disabled={busy !== null || !text.trim()}>{busy === "add" ? <Spinner /> : <Save size={13} />} Add note</button>
        </div>
      </form>
      {listing.notes.length > 0 && (
        <ul className="mt-2 space-y-1.5">
          {listing.notes.map((n) => (
            <li key={n.id} className={`rounded border p-2 text-sm ${n.flagged && !n.resolved ? "border-amber/40 bg-amber/5" : "border-border"} ${n.resolved ? "opacity-60" : ""}`}>
              <div className={`whitespace-pre-wrap ${n.resolved ? "line-through" : ""}`}>{n.text}</div>
              <div className="mt-1 flex items-center gap-1.5 text-[11px] text-dim">
                <span className="num" title={fmtDate(n.created_at)}>{relTime(n.created_at)}</span>
                <span className="flex-1" />
                <button className="btn btn-ghost btn-xs" onClick={() => patch(n.id, { flagged: !n.flagged })} disabled={busy !== null} title={n.flagged ? "Unflag" : "Flag for investigation"}>{n.flagged ? <FlagOff size={11} /> : <Flag size={11} />}</button>
                <button className="btn btn-ghost btn-xs" onClick={() => patch(n.id, { resolved: !n.resolved })} disabled={busy !== null} title={n.resolved ? "Reopen" : "Mark resolved"}><CheckCircle2 size={11} className={n.resolved ? "text-green" : ""} /></button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function OutcomePanel({ listing, onUpdate, platforms }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void; platforms: string[] }) {
  const toast = useToast();
  const o = listing.outcome;
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({
    purchased: o?.purchased ?? false, purchase_price: o?.purchase_price?.toString() ?? "", acquisition_expenses: o?.acquisition_expenses?.toString() ?? "", purchased_at: toLocalInputValue(o?.purchased_at),
    sold: o?.sold ?? false, resale_price: o?.resale_price?.toString() ?? "", selling_fees: o?.selling_fees?.toString() ?? "", resale_platform: o?.resale_platform ?? "", sold_at: toLocalInputValue(o?.sold_at), notes: o?.notes ?? "",
  });
  async function save(e: React.FormEvent) {
    e.preventDefault();
    const body: OutcomeIn = {
      purchased: f.purchased, purchase_price: numOrNull(f.purchase_price), acquisition_expenses: numOrNull(f.acquisition_expenses), purchased_at: fromLocalInputValue(f.purchased_at),
      sold: f.sold, resale_price: numOrNull(f.resale_price), selling_fees: numOrNull(f.selling_fees), resale_platform: f.resale_platform || null, sold_at: fromLocalInputValue(f.sold_at), notes: f.notes || null,
    };
    setBusy(true);
    try { const d = await api.putOutcome(listing.id, body); onUpdate(d); toast.success("Outcome saved"); }
    catch (err) { toast.apiError(err, "Save outcome"); } finally { setBusy(false); }
  }
  return (
    <Card title="Outcome (actuals)" actions={o?.realized_profit != null ? <span className={`num text-sm font-semibold ${o.realized_profit >= 0 ? "text-green" : "text-red"}`}>realized {money(o.realized_profit)}</span> : null}>
      <form onSubmit={save} className="grid grid-cols-2 gap-2">
        <label className="col-span-2 flex items-center gap-2 text-sm"><input type="checkbox" checked={f.purchased} onChange={(e) => setF({ ...f, purchased: e.target.checked })} /> Purchased</label>
        <Field label="Purchase price (hammer)"><input className="input" type="number" step="0.01" min="0" value={f.purchase_price} onChange={(e) => setF({ ...f, purchase_price: e.target.value })} /></Field>
        <Field label="Acquisition expenses" hint="shipping, premium, tax"><input className="input" type="number" step="0.01" min="0" value={f.acquisition_expenses} onChange={(e) => setF({ ...f, acquisition_expenses: e.target.value })} /></Field>
        <Field label="Purchased at" className="col-span-2"><input className="input" type="datetime-local" value={f.purchased_at} onChange={(e) => setF({ ...f, purchased_at: e.target.value })} /></Field>
        <label className="col-span-2 mt-1 flex items-center gap-2 text-sm"><input type="checkbox" checked={f.sold} onChange={(e) => setF({ ...f, sold: e.target.checked })} /> Sold</label>
        <Field label="Resale price"><input className="input" type="number" step="0.01" min="0" value={f.resale_price} onChange={(e) => setF({ ...f, resale_price: e.target.value })} /></Field>
        <Field label="Selling fees"><input className="input" type="number" step="0.01" min="0" value={f.selling_fees} onChange={(e) => setF({ ...f, selling_fees: e.target.value })} /></Field>
        <Field label="Platform"><select className="input" value={f.resale_platform} onChange={(e) => setF({ ...f, resale_platform: e.target.value })}><option value="">—</option>{platforms.map((p) => <option key={p} value={p}>{p}</option>)}</select></Field>
        <Field label="Sold at"><input className="input" type="datetime-local" value={f.sold_at} onChange={(e) => setF({ ...f, sold_at: e.target.value })} /></Field>
        <Field label="Notes" className="col-span-2"><input className="input" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        <div className="col-span-2 flex items-center justify-between">
          <span className="num text-[11px] text-dim">{o?.days_to_sale != null ? `${num(o.days_to_sale)} days to sale` : ""}</span>
          <button className="btn btn-sm btn-primary" disabled={busy}>{busy ? <Spinner /> : <Save size={13} />} Save outcome</button>
        </div>
      </form>
    </Card>
  );
}
