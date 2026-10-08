"use client";
import { ExternalLink, Pencil, Save } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, fromLocalInputValue, money, num, numOrNull, relTime, toLocalInputValue } from "@/lib/format";
import type { ListingDetail, ListingPatch, SnapshotIn } from "@/lib/types";
import { Countdown } from "@/components/listings/countdown";
import { Badge, DemoBadge, StatusBadge } from "@/components/ui/badges";
import { Card, Field, KV, Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

export function AuctionInfo({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const l = listing;
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Card title="Original auction data">
        <KV rows={[
          ["Title", l.title],
          ["Source", <span key="s" className="flex items-center gap-1.5">{l.source}{l.is_demo && <DemoBadge />}{l.extraction_method && <span className="text-dim">· {l.extraction_method}</span>}</span>],
          ["Item ID", <span key="i" className="num">{l.source_item_id || "—"}</span>],
          ["URL", l.source_url ? <a key="u" href={l.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-accent hover:underline">{l.source_url} <ExternalLink size={11} /></a> : null],
          ["Seller", l.seller],
          ["Category", l.category],
          ["Domain", <span key="d" className="capitalize">{l.domain || "unknown"}</span>],
          ["Status", <span key="st" className="flex items-center gap-1.5"><StatusBadge status={l.status} />{l.archived && <Badge tone="gray">archived</Badge>}</span>],
          ["Current bid", <span key="b" className="num">{money(l.current_bid)} <span className="text-dim">({num(l.num_bids)} bids)</span></span>],
          ["Buy now", <span key="bn" className="num">{money(l.buy_now_price)}</span>],
          ["Ends", <span key="e" className="flex items-center gap-2"><span className="num">{fmtDate(l.ends_at)}</span><Countdown endsAt={l.ends_at} /></span>],
          ["Shipping", <span key="sh" className="num">{money(l.shipping_cost)}{l.handling_fee != null ? <span className="text-dim"> + handling {money(l.handling_fee)}</span> : null}</span>],
          ["Other costs", Object.keys(l.other_costs || {}).length ? <span key="oc" className="num">{Object.entries(l.other_costs).map(([k, v]) => `${k}: ${money(v)}`).join(", ")}</span> : null],
          ["Condition", l.condition_text],
          ["Measurements", Object.keys(l.measurements || {}).length ? <span key="m" className="num">{Object.entries(l.measurements).map(([k, v]) => `${k}: ${String(v)}`).join(" · ")}</span> : null],
          ["Assumptions", Object.keys(l.assumptions || {}).length ? <span key="a" className="num">{Object.entries(l.assumptions).map(([k, v]) => `${k}: ${String(v)}`).join(" · ")}</span> : <span key="a2" className="text-dim">none (settings defaults apply)</span>],
          ["First seen", <span key="fs" className="num">{fmtDate(l.first_seen_at)} <span className="text-dim">({relTime(l.first_seen_at)})</span></span>],
          ["Last updated", <span key="lu" className="num">{fmtDate(l.last_updated_at)} <span className="text-dim">({relTime(l.last_updated_at)})</span></span>],
          ["Last verified", <span key="lv" className="num">{fmtDate(l.last_verified_at)}</span>],
        ]} />
        {l.description && (
          <div className="mt-3">
            <div className="label">Seller description</div>
            <p className="whitespace-pre-wrap rounded bg-elev-2/60 p-2 text-sm text-muted">{l.description}</p>
          </div>
        )}
        {l.user_notes && (
          <div className="mt-3">
            <div className="label">Your notes on the listing</div>
            <p className="whitespace-pre-wrap text-sm">{l.user_notes}</p>
          </div>
        )}
      </Card>
      <div className="flex flex-col gap-3">
        <SnapshotForm listing={l} onUpdate={onUpdate} />
        <Card title={`Price / status history (${l.snapshots.length})`} bodyClass="p-0">
          {l.snapshots.length === 0 ? <p className="p-3 text-xs text-dim">No snapshots yet.</p> : (
            <div className="scrollbar-thin max-h-64 overflow-auto">
              <table className="tbl">
                <thead><tr><th>Captured</th><th>Source</th><th className="r">Bid</th><th className="r">Bids</th><th>Ends</th><th className="r">Ship</th><th>Status</th></tr></thead>
                <tbody>
                  {[...l.snapshots].reverse().map((s) => (
                    <tr key={s.id}>
                      <td className="num whitespace-nowrap">{fmtDate(s.captured_at)}</td>
                      <td>{s.source}</td>
                      <td className="r num">{money(s.current_bid)}</td>
                      <td className="r num">{num(s.num_bids)}</td>
                      <td className="num whitespace-nowrap">{fmtDate(s.ends_at)}</td>
                      <td className="r num">{money(s.shipping_cost)}</td>
                      <td>{s.status || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <EditListingForm listing={l} onUpdate={onUpdate} />
      </div>
    </div>
  );
}

function SnapshotForm({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({
    current_bid: listing.current_bid?.toString() ?? "",
    num_bids: listing.num_bids?.toString() ?? "",
    ends_at: toLocalInputValue(listing.ends_at),
    shipping_cost: listing.shipping_cost?.toString() ?? "",
    handling_fee: listing.handling_fee?.toString() ?? "",
    status: listing.status ?? "active",
  });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: SnapshotIn = {};
    const cb = numOrNull(f.current_bid); if (cb !== null) body.current_bid = cb;
    const nb = numOrNull(f.num_bids); if (nb !== null) body.num_bids = Math.round(nb);
    const ea = fromLocalInputValue(f.ends_at); if (ea) body.ends_at = ea;
    const sc = numOrNull(f.shipping_cost); if (sc !== null) body.shipping_cost = sc;
    const hf = numOrNull(f.handling_fee); if (hf !== null) body.handling_fee = hf;
    if (f.status) body.status = f.status;
    setBusy(true);
    try {
      const d = await api.snapshot(listing.id, body);
      onUpdate(d);
      toast.success("Snapshot recorded", "Opportunity recomputed with the new price/status.");
    } catch (err) { toast.apiError(err, "Record snapshot"); } finally { setBusy(false); }
  }
  return (
    <Card title="Manual update: price / status" actions={<span className="text-[11px] text-dim">records a snapshot</span>}>
      <form onSubmit={submit} className="grid grid-cols-3 gap-2">
        <Field label="Current bid"><input className="input" type="number" step="0.01" min="0" value={f.current_bid} onChange={(e) => setF({ ...f, current_bid: e.target.value })} /></Field>
        <Field label="# bids"><input className="input" type="number" step="1" min="0" value={f.num_bids} onChange={(e) => setF({ ...f, num_bids: e.target.value })} /></Field>
        <Field label="Status">
          <select className="input" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
            <option value="active">active</option><option value="ended">ended</option><option value="sold">sold</option><option value="cancelled">cancelled</option>
          </select>
        </Field>
        <Field label="Ends at (local)" className="col-span-3 sm:col-span-1"><input className="input" type="datetime-local" value={f.ends_at} onChange={(e) => setF({ ...f, ends_at: e.target.value })} /></Field>
        <Field label="Shipping"><input className="input" type="number" step="0.01" min="0" value={f.shipping_cost} onChange={(e) => setF({ ...f, shipping_cost: e.target.value })} /></Field>
        <Field label="Handling"><input className="input" type="number" step="0.01" min="0" value={f.handling_fee} onChange={(e) => setF({ ...f, handling_fee: e.target.value })} /></Field>
        <div className="col-span-3 flex justify-end"><button className="btn btn-sm btn-primary" disabled={busy}>{busy ? <Spinner /> : <Save size={13} />} Record snapshot</button></div>
      </form>
    </Card>
  );
}

function EditListingForm({ listing, onUpdate }: { listing: ListingDetail; onUpdate: (d: ListingDetail) => void }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({
    title: listing.title, category: listing.category ?? "", seller: listing.seller ?? "", domain: listing.domain ?? "unknown",
    condition_text: listing.condition_text ?? "", description: listing.description ?? "", source_url: listing.source_url ?? "",
    user_notes: listing.user_notes ?? "", archived: listing.archived,
    measurements: JSON.stringify(listing.measurements ?? {}, null, 0), other_costs: JSON.stringify(listing.other_costs ?? {}, null, 0), assumptions: JSON.stringify(listing.assumptions ?? {}, null, 0),
  });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: ListingPatch = {};
    if (f.title !== listing.title) body.title = f.title;
    if (f.category !== (listing.category ?? "")) body.category = f.category || null;
    if (f.seller !== (listing.seller ?? "")) body.seller = f.seller || null;
    if (f.domain !== (listing.domain ?? "unknown")) body.domain = f.domain;
    if (f.condition_text !== (listing.condition_text ?? "")) body.condition_text = f.condition_text || null;
    if (f.description !== (listing.description ?? "")) body.description = f.description || null;
    if (f.source_url !== (listing.source_url ?? "")) body.source_url = f.source_url || null;
    if (f.user_notes !== (listing.user_notes ?? "")) body.user_notes = f.user_notes || null;
    if (f.archived !== listing.archived) body.archived = f.archived;
    try {
      for (const k of ["measurements", "other_costs", "assumptions"] as const) {
        const parsed = JSON.parse(f[k] || "{}");
        if (typeof parsed !== "object" || Array.isArray(parsed)) throw new Error(`${k} must be a JSON object`);
        if (JSON.stringify(parsed) !== JSON.stringify(listing[k] ?? {})) body[k] = parsed;
      }
    } catch (err) { toast.error("Invalid JSON", (err as Error).message); return; }
    if (!Object.keys(body).length) { toast.info("No changes"); return; }
    setBusy(true);
    try {
      const d = await api.patchListing(listing.id, body);
      onUpdate(d);
      toast.success("Listing updated");
      setOpen(false);
    } catch (err) { toast.apiError(err, "Update listing"); } finally { setBusy(false); }
  }
  return (
    <Card title="Edit listing fields" actions={<button className="btn btn-xs" onClick={() => setOpen((v) => !v)}><Pencil size={11} /> {open ? "Close" : "Edit"}</button>}>
      {!open ? <p className="text-xs text-dim">Correct title/category/domain, add listing-level cost assumptions (e.g. <code className="num">{"{\"outgoing_shipping\": 28}"}</code>), archive.</p> : (
        <form onSubmit={submit} className="grid grid-cols-2 gap-2">
          <Field label="Title" className="col-span-2"><input className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} required /></Field>
          <Field label="Category"><input className="input" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} /></Field>
          <Field label="Seller"><input className="input" value={f.seller} onChange={(e) => setF({ ...f, seller: e.target.value })} /></Field>
          <Field label="Domain">
            <select className="input" value={f.domain} onChange={(e) => setF({ ...f, domain: e.target.value })}>
              <option value="clothing">clothing</option><option value="jewelry">jewelry</option><option value="other">other</option><option value="unknown">unknown</option>
            </select>
          </Field>
          <Field label="Source URL"><input className="input" value={f.source_url} onChange={(e) => setF({ ...f, source_url: e.target.value })} placeholder="https://" /></Field>
          <Field label="Condition text" className="col-span-2"><input className="input" value={f.condition_text} onChange={(e) => setF({ ...f, condition_text: e.target.value })} /></Field>
          <Field label="Description" className="col-span-2"><textarea className="input" rows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
          <Field label="Measurements (JSON)"><input className="input num" value={f.measurements} onChange={(e) => setF({ ...f, measurements: e.target.value })} /></Field>
          <Field label="Other costs (JSON)"><input className="input num" value={f.other_costs} onChange={(e) => setF({ ...f, other_costs: e.target.value })} /></Field>
          <Field label="Finance assumptions (JSON)" className="col-span-2" hint="Keys: incoming_shipping, outgoing_shipping, sales_tax_pct, cleaning_repair_cost, packaging_cost, platform"><input className="input num" value={f.assumptions} onChange={(e) => setF({ ...f, assumptions: e.target.value })} /></Field>
          <Field label="Your notes" className="col-span-2"><textarea className="input" rows={2} value={f.user_notes} onChange={(e) => setF({ ...f, user_notes: e.target.value })} /></Field>
          <label className="col-span-2 flex items-center gap-2 text-sm"><input type="checkbox" checked={f.archived} onChange={(e) => setF({ ...f, archived: e.target.checked })} /> Archived (hidden from dashboard)</label>
          <div className="col-span-2 flex justify-end gap-1.5">
            <button type="button" className="btn btn-sm" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-sm btn-primary" disabled={busy}>{busy ? <Spinner /> : <Save size={13} />} Save changes</button>
          </div>
        </form>
      )}
    </Card>
  );
}
