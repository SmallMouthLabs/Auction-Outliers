"use client";
import { BookOpen, Pencil, Plus, Search, Sprout, Trash2, X } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { ReferenceEntry, ReferenceIn } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { Badge, DemoBadge } from "@/components/ui/badges";
import { ApiErrorAlert, Card, EmptyState, Field, Skeleton, Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

const TYPES = ["brand", "designer", "maker_mark", "product", "characteristic", "hallmark", "other"];

export default function ReferencePage() {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [qi, setQi] = useState("");
  const [domain, setDomain] = useState("");
  const list = useApi(() => api.references(q || undefined, domain || undefined), [q, domain]);
  const [editing, setEditing] = useState<ReferenceEntry | "new" | null>(null);
  const [busy, setBusy] = useState<number | "seed" | null>(null);

  async function del(r: ReferenceEntry) {
    if (!confirm(`Delete reference "${r.name}"?`)) return;
    setBusy(r.id);
    try { await api.deleteReference(r.id); await list.refresh(); toast.info("Reference deleted"); }
    catch (e) { toast.apiError(e, "Delete reference"); } finally { setBusy(null); }
  }
  async function seed() {
    setBusy("seed");
    try { await api.seedReferences(); await list.refresh(); toast.success("Seed references loaded"); }
    catch (e) { toast.apiError(e, "Seed references"); } finally { setBusy(null); }
  }
  const items = list.data?.items ?? [];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Reference database</h1>
          <p className="text-xs text-muted">Makers, marks, labels and characteristics the identifier matches against. Typical prices are approximate guidance; verify with sold comps.</p>
        </div>
        <div className="flex gap-1.5">
          <button className="btn btn-sm" onClick={seed} disabled={busy !== null}><Sprout size={13} /> Load seed entries</button>
          <button className="btn btn-sm btn-primary" onClick={() => setEditing("new")}><Plus size={13} /> Add entry</button>
        </div>
      </div>
      <form className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-elev px-3 py-2" onSubmit={(e) => { e.preventDefault(); setQ(qi); }}>
        <div className="relative min-w-[220px] flex-1">
          <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-dim" />
          <input className="input pl-7" placeholder="Search name, identifiers, keywords…" value={qi} onChange={(e) => setQi(e.target.value)} />
        </div>
        <select className="input w-auto" value={domain} onChange={(e) => setDomain(e.target.value)}><option value="">All domains</option><option value="clothing">Clothing</option><option value="jewelry">Jewelry</option></select>
        <button className="btn btn-sm">Search</button>
        {(q || domain) && <button type="button" className="btn btn-sm btn-ghost" onClick={() => { setQ(""); setQi(""); setDomain(""); }}><X size={13} /> Clear</button>}
      </form>
      {editing && <EditForm entry={editing === "new" ? null : editing} onClose={() => setEditing(null)} onSaved={async () => { setEditing(null); await list.refresh(); }} />}
      {list.error && <ApiErrorAlert error={list.error} />}
      {list.loading && !list.data ? <Skeleton className="h-40" /> : items.length === 0 ? (
        <EmptyState icon={<BookOpen size={26} />} title="No reference entries">Add your own or load the seed set of common makers and marks.</EmptyState>
      ) : (
        <div className="scrollbar-thin overflow-x-auto rounded-lg border border-border bg-elev">
          <table className="tbl min-w-[900px]">
            <thead><tr><th>Name</th><th>Type</th><th>Domain</th><th>Identifiers / keywords</th><th className="r">Typical</th><th>Demand</th><th>Liq.</th><th>Source</th><th></th></tr></thead>
            <tbody>{items.map((r) => (
              <tr key={r.id}>
                <td className="max-w-[300px]"><div className="flex items-center gap-1.5"><span className="font-medium">{r.name}</span>{r.is_demo && <DemoBadge />}</div><div className="text-xs text-muted">{r.characteristics}</div>{r.id_confidence_notes && <div className="text-[11px] text-dim">{r.id_confidence_notes}</div>}</td>
                <td className="text-xs">{r.entry_type}<div className="text-dim">{r.category}</div></td>
                <td className="capitalize">{r.domain}</td>
                <td className="max-w-[260px] text-[11px]"><div className="flex flex-wrap gap-1">{r.identifiers.map((x) => <Badge key={"i" + x} tone="accent">{x}</Badge>)}{r.keywords.map((x) => <Badge key={"k" + x} tone="gray">{x}</Badge>)}</div></td>
                <td className="r num whitespace-nowrap">{money(r.typical_low, { cents: false })}–{money(r.typical_high, { cents: false })}</td>
                <td>{r.demand}</td><td>{r.liquidity}</td>
                <td className="max-w-[140px] truncate text-xs text-dim" title={r.source}>{r.source}</td>
                <td><div className="flex gap-1"><button className="btn btn-xs" onClick={() => setEditing(r)} aria-label="Edit"><Pencil size={11} /></button><button className="btn btn-xs btn-danger" onClick={() => del(r)} disabled={busy === r.id} aria-label="Delete">{busy === r.id ? <Spinner size={11} /> : <Trash2 size={11} />}</button></div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function EditForm({ entry, onClose, onSaved }: { entry: ReferenceEntry | null; onClose: () => void; onSaved: () => Promise<void> }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({
    name: entry?.name ?? "", entry_type: entry?.entry_type ?? "brand", domain: entry?.domain ?? "clothing", category: entry?.category ?? "", characteristics: entry?.characteristics ?? "",
    identifiers: entry?.identifiers.join(", ") ?? "", keywords: entry?.keywords.join(", ") ?? "", reference_image_urls: entry?.reference_image_urls.join("\n") ?? "",
    typical_low: entry?.typical_low?.toString() ?? "", typical_high: entry?.typical_high?.toString() ?? "", demand: entry?.demand ?? "medium", liquidity: entry?.liquidity ?? "medium", id_confidence_notes: entry?.id_confidence_notes ?? "", source: entry?.source ?? "user",
  });
  const split = (s: string) => s.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: ReferenceIn = {
      name: f.name.trim(), entry_type: f.entry_type, domain: f.domain, category: f.category || null, characteristics: f.characteristics || null,
      identifiers: split(f.identifiers), keywords: split(f.keywords), reference_image_urls: split(f.reference_image_urls), price_evidence: entry?.price_evidence ?? [],
      typical_low: f.typical_low === "" ? null : Number(f.typical_low), typical_high: f.typical_high === "" ? null : Number(f.typical_high), demand: f.demand, liquidity: f.liquidity,
      id_confidence_notes: f.id_confidence_notes || null, source: f.source || "user",
    };
    setBusy(true);
    try {
      if (entry) await api.updateReference(entry.id, body); else await api.createReference(body);
      toast.success(entry ? "Reference updated" : "Reference added");
      await onSaved();
    } catch (err) { toast.apiError(err, "Save reference"); } finally { setBusy(false); }
  }
  return (
    <Card title={entry ? `Edit: ${entry.name}` : "New reference entry"} actions={<button className="btn btn-xs" onClick={onClose}><X size={11} /> Close</button>}>
      <form onSubmit={submit} className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Field label="Name *" className="col-span-2"><input className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Type"><select className="input" value={f.entry_type} onChange={(e) => setF({ ...f, entry_type: e.target.value })}>{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select></Field>
        <Field label="Domain"><select className="input" value={f.domain} onChange={(e) => setF({ ...f, domain: e.target.value })}><option value="clothing">clothing</option><option value="jewelry">jewelry</option></select></Field>
        <Field label="Category"><input className="input" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} /></Field>
        <Field label="Typical low $"><input className="input" type="number" step="1" min="0" value={f.typical_low} onChange={(e) => setF({ ...f, typical_low: e.target.value })} /></Field>
        <Field label="Typical high $"><input className="input" type="number" step="1" min="0" value={f.typical_high} onChange={(e) => setF({ ...f, typical_high: e.target.value })} /></Field>
        <Field label="Source"><input className="input" value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })} /></Field>
        <Field label="Demand"><select className="input" value={f.demand} onChange={(e) => setF({ ...f, demand: e.target.value })}><option>high</option><option>medium</option><option>low</option></select></Field>
        <Field label="Liquidity"><select className="input" value={f.liquidity} onChange={(e) => setF({ ...f, liquidity: e.target.value })}><option>high</option><option>medium</option><option>low</option></select></Field>
        <Field label="Characteristics" className="col-span-2 md:col-span-4"><textarea className="input" rows={2} value={f.characteristics} onChange={(e) => setF({ ...f, characteristics: e.target.value })} placeholder="How to recognise it: label styles, construction, marks…" /></Field>
        <Field label="Identifiers (exact strings, comma separated)" className="col-span-2"><input className="input" value={f.identifiers} onChange={(e) => setF({ ...f, identifiers: e.target.value })} placeholder="J97, carhartt made in usa" /></Field>
        <Field label="Keywords (comma separated)" className="col-span-2"><input className="input" value={f.keywords} onChange={(e) => setF({ ...f, keywords: e.target.value })} /></Field>
        <Field label="Reference image URLs (one per line)" className="col-span-2"><textarea className="input num" rows={2} value={f.reference_image_urls} onChange={(e) => setF({ ...f, reference_image_urls: e.target.value })} /></Field>
        <Field label="ID confidence notes" className="col-span-2"><textarea className="input" rows={2} value={f.id_confidence_notes} onChange={(e) => setF({ ...f, id_confidence_notes: e.target.value })} /></Field>
        <div className="col-span-2 flex justify-end gap-1.5 md:col-span-4"><button type="button" className="btn btn-sm" onClick={onClose}>Cancel</button><button className="btn btn-sm btn-primary" disabled={busy}>{busy ? <Spinner /> : null} {entry ? "Save" : "Add"}</button></div>
      </form>
    </Card>
  );
}
