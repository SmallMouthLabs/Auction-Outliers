"use client";
import { FileSpreadsheet, FileText, Globe, ImagePlus, Mail, Plus } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { fromLocalInputValue, numOrNull } from "@/lib/format";
import type { ImportResult, ListingIn } from "@/lib/types";
import { Alert, Card, Field, Pre, Spinner, Tabs, Toggle } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

type Mode = "manual" | "csv" | "email" | "page";

export default function ImportPage() {
  const [mode, setMode] = useState<Mode>("manual");
  const [fetchImages, setFetchImages] = useState(true);
  const [analyze, setAnalyze] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const opts = { fetch_images: fetchImages, analyze };
  return (
    <div className="flex flex-col gap-3">
      <div>
        <h1 className="text-lg font-semibold">Import listings</h1>
        <p className="text-xs text-muted">Bring auctions in by hand, from a CSV export, from a ShopGoodwill Personal Shopper e-mail, or from a saved item page. Re-importing the same source item updates it and records a price snapshot.</p>
      </div>
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-elev px-3 py-2">
        <span className="text-xs font-medium uppercase tracking-wider text-muted">Options</span>
        <Toggle checked={fetchImages} onChange={setFetchImages} label="Fetch image URLs" />
        <Toggle checked={analyze} onChange={setAnalyze} label="Queue AI analysis (background job, mode auto)" />
      </div>
      <Tabs tabs={[
        { id: "manual", label: <span className="flex items-center gap-1.5"><Plus size={13} /> Manual form</span> },
        { id: "csv", label: <span className="flex items-center gap-1.5"><FileSpreadsheet size={13} /> CSV</span> },
        { id: "email", label: <span className="flex items-center gap-1.5"><Mail size={13} /> Personal Shopper e-mail</span> },
        { id: "page", label: <span className="flex items-center gap-1.5"><Globe size={13} /> Saved item page</span> },
      ]} value={mode} onChange={setMode} />
      <div className="grid gap-3 xl:grid-cols-[1fr_420px]">
        <div>
          {mode === "manual" && <ManualForm opts={opts} onResult={setResult} />}
          {mode === "csv" && <CsvImport opts={opts} onResult={setResult} />}
          {mode === "email" && <EmailImport opts={opts} onResult={setResult} />}
          {mode === "page" && <PageImport opts={opts} onResult={setResult} />}
        </div>
        <ResultPanel result={result} />
      </div>
    </div>
  );
}

type Opts = { fetch_images: boolean; analyze: boolean };

function ResultPanel({ result }: { result: ImportResult | null }) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [target, setTarget] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  if (!result) return <Card title="Import result"><p className="text-xs text-dim">Results appear here: created / updated / unchanged counts, parse errors and a preview of parsed fields.</p></Card>;
  const ids = result.ids ?? [];
  async function upload(files: FileList | null) {
    const id = target ?? ids[0];
    if (!files?.length || !id) return;
    setBusy(true);
    try { const r = await api.uploadImages(id, Array.from(files)); toast.success(`Uploaded ${r.images.length} photo(s) to listing #${id}`); }
    catch (e) { toast.apiError(e, "Photo upload"); } finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  }
  return (
    <Card title="Import result">
      <div className="grid grid-cols-3 gap-1.5 text-center">
        <div className="rounded border border-green/30 bg-green/10 p-2"><div className="num text-xl font-semibold text-green">{result.created}</div><div className="text-[10px] uppercase text-muted">created</div></div>
        <div className="rounded border border-blue/30 bg-blue/10 p-2"><div className="num text-xl font-semibold text-blue">{result.updated}</div><div className="text-[10px] uppercase text-muted">updated</div></div>
        <div className="rounded border border-border p-2"><div className="num text-xl font-semibold">{result.unchanged}</div><div className="text-[10px] uppercase text-muted">unchanged</div></div>
      </div>
      {result.errors?.length > 0 && <Alert kind="error" title={`${result.errors.length} error${result.errors.length === 1 ? "" : "s"}`} className="mt-2"><ul className="list-disc pl-4">{result.errors.map((e, i) => <li key={i}>{e}</li>)}</ul></Alert>}
      {ids.length > 0 && (
        <div className="mt-2">
          <div className="label">Listings</div>
          <div className="flex flex-wrap gap-1">{ids.map((id) => <Link key={id} href={`/items/${id}`} className="btn btn-xs">#{id}</Link>)}</div>
          <div className="mt-2 flex items-center gap-1.5">
            <select className="input w-auto py-0.5" value={target ?? ids[0]} onChange={(e) => setTarget(Number(e.target.value))} aria-label="Listing for photo upload">{ids.map((id) => <option key={id} value={id}>#{id}</option>)}</select>
            <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => upload(e.target.files)} />
            <button className="btn btn-sm" onClick={() => fileRef.current?.click()} disabled={busy}>{busy ? <Spinner /> : <ImagePlus size={13} />} Upload photos</button>
          </div>
        </div>
      )}
      {result.parsed !== undefined && (
        <div className="mt-2"><div className="label">Parsed preview</div><Pre data={result.parsed} className="max-h-96" /></div>
      )}
    </Card>
  );
}

function ManualForm({ opts, onResult }: { opts: Opts; onResult: (r: ImportResult) => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const blank = { title: "", source_url: "", source_item_id: "", description: "", category: "", seller: "", domain: "", current_bid: "", num_bids: "", buy_now_price: "", ends_at: "", shipping_cost: "", handling_fee: "", condition_text: "", image_urls: "" };
  const [f, setF] = useState(blank);
  const set = (k: keyof typeof blank) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: ListingIn = {
      source: "manual", title: f.title.trim(), source_url: f.source_url || null, source_item_id: f.source_item_id || null, description: f.description || null, category: f.category || null, seller: f.seller || null,
      domain: f.domain || null, current_bid: numOrNull(f.current_bid), num_bids: numOrNull(f.num_bids) === null ? null : Math.round(Number(f.num_bids)), buy_now_price: numOrNull(f.buy_now_price),
      ends_at: fromLocalInputValue(f.ends_at), shipping_cost: numOrNull(f.shipping_cost), handling_fee: numOrNull(f.handling_fee), condition_text: f.condition_text || null,
      image_urls: f.image_urls.split(/\s+/).map((u) => u.trim()).filter((u) => /^https?:\/\//i.test(u)),
    };
    setBusy(true);
    try {
      const r = await api.createListing(body, opts);
      onResult({ created: r.created ? 1 : 0, updated: !r.created && r.changed ? 1 : 0, unchanged: !r.created && !r.changed ? 1 : 0, ids: [r.listing.id], errors: [], parsed: body });
      toast.success(r.created ? `Listing #${r.listing.id} created` : `Listing #${r.listing.id} ${r.changed ? "updated" : "unchanged"}`, opts.analyze ? "Analysis job queued." : undefined);
      if (r.created) setF(blank);
    } catch (err) { toast.apiError(err, "Create listing"); } finally { setBusy(false); }
  }
  return (
    <Card title="Manual listing">
      <form onSubmit={submit} className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Field label="Title *" className="col-span-2 md:col-span-4"><input className="input" required value={f.title} onChange={set("title")} placeholder="Auction title as listed" /></Field>
        <Field label="Auction URL" className="col-span-2"><input className="input" value={f.source_url} onChange={set("source_url")} placeholder="https://shopgoodwill.com/item/..." /></Field>
        <Field label="Source item ID" hint="used for de-duplication"><input className="input" value={f.source_item_id} onChange={set("source_item_id")} /></Field>
        <Field label="Domain"><select className="input" value={f.domain} onChange={set("domain")}><option value="">auto / unknown</option><option value="clothing">clothing</option><option value="jewelry">jewelry</option><option value="other">other</option></select></Field>
        <Field label="Category" className="col-span-2"><input className="input" value={f.category} onChange={set("category")} placeholder="Clothing > Women's > Sweaters" /></Field>
        <Field label="Seller" className="col-span-2"><input className="input" value={f.seller} onChange={set("seller")} /></Field>
        <Field label="Current bid"><input className="input" type="number" step="0.01" min="0" value={f.current_bid} onChange={set("current_bid")} /></Field>
        <Field label="# bids"><input className="input" type="number" step="1" min="0" value={f.num_bids} onChange={set("num_bids")} /></Field>
        <Field label="Buy now price"><input className="input" type="number" step="0.01" min="0" value={f.buy_now_price} onChange={set("buy_now_price")} /></Field>
        <Field label="Ends at (local)"><input className="input" type="datetime-local" value={f.ends_at} onChange={set("ends_at")} /></Field>
        <Field label="Shipping cost"><input className="input" type="number" step="0.01" min="0" value={f.shipping_cost} onChange={set("shipping_cost")} /></Field>
        <Field label="Handling fee"><input className="input" type="number" step="0.01" min="0" value={f.handling_fee} onChange={set("handling_fee")} /></Field>
        <Field label="Condition" className="col-span-2"><input className="input" value={f.condition_text} onChange={set("condition_text")} /></Field>
        <Field label="Description" className="col-span-2 md:col-span-4"><textarea className="input" rows={3} value={f.description} onChange={set("description")} /></Field>
        <Field label="Image URLs (one per line)" className="col-span-2 md:col-span-4" hint="You can also upload photos after creation."><textarea className="input num" rows={3} value={f.image_urls} onChange={set("image_urls")} placeholder="https://..." /></Field>
        <div className="col-span-2 flex justify-end md:col-span-4"><button className="btn btn-sm btn-primary" disabled={busy}>{busy ? <Spinner /> : <Plus size={13} />} Create listing</button></div>
      </form>
    </Card>
  );
}

function CsvImport({ opts, onResult }: { opts: Opts; onResult: (r: ImportResult) => void }) {
  const toast = useToast();
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  async function run() {
    if (!file) return;
    setBusy(true);
    try { const r = await api.importCsv(file, opts); onResult(r); toast.success(`CSV imported: ${r.created} created, ${r.updated} updated`, r.errors.length ? `${r.errors.length} row error(s)` : undefined); }
    catch (e) { toast.apiError(e, "CSV import"); } finally { setBusy(false); }
  }
  return (
    <Card title="CSV import">
      <p className="mb-2 text-xs text-muted">Header row with any of: <code className="num">title, source_url, source_item_id, description, category, seller, domain, current_bid, num_bids, buy_now_price, ends_at, shipping_cost, handling_fee, condition_text, image_urls</code> (image_urls separated by <code className="num">|</code>). Title is required per row.</p>
      <input ref={ref} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <div className="flex items-center gap-2">
        <button className="btn btn-sm" onClick={() => ref.current?.click()}><FileSpreadsheet size={13} /> Choose CSV</button>
        <span className="text-xs text-muted">{file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : "no file selected"}</span>
        <button className="btn btn-sm btn-primary ml-auto" onClick={run} disabled={!file || busy}>{busy ? <Spinner /> : null} Import</button>
      </div>
    </Card>
  );
}

function EmailImport({ opts, onResult }: { opts: Opts; onResult: (r: ImportResult) => void }) {
  const toast = useToast();
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [html, setHtml] = useState("");
  async function run() {
    if (!file && !html.trim()) { toast.error("Provide an .eml file or paste the e-mail HTML"); return; }
    setBusy(true);
    try { const r = await api.importEmail(file ? { file } : { html }, opts); onResult(r); toast.success(`E-mail parsed: ${r.created} created, ${r.updated} updated`, r.errors.length ? r.errors[0] : undefined); }
    catch (e) { toast.apiError(e, "E-mail import"); } finally { setBusy(false); }
  }
  return (
    <Card title="ShopGoodwill Personal Shopper e-mail">
      <p className="mb-2 text-xs text-muted">Save the notification e-mail as <code className="num">.eml</code> (Gmail: ⋮ → Download message) and upload it, or paste the e-mail HTML. Every <code className="num">shopgoodwill.com/item/&lt;id&gt;</code> link becomes a listing. IMAP polling needs <code className="num">OUTLIER_IMAP_*</code> in .env.</p>
      <input ref={ref} type="file" accept=".eml,message/rfc822,.html,text/html" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <div className="flex items-center gap-2">
        <button className="btn btn-sm" onClick={() => ref.current?.click()}><Mail size={13} /> Choose .eml</button>
        <span className="text-xs text-muted">{file ? file.name : "no file selected"}</span>
        {file && <button className="btn btn-xs" onClick={() => { setFile(null); if (ref.current) ref.current.value = ""; }}>clear</button>}
      </div>
      <Field label="…or paste e-mail HTML" className="mt-2"><textarea className="input num" rows={8} value={html} onChange={(e) => setHtml(e.target.value)} disabled={!!file} placeholder="<html>…" /></Field>
      <div className="mt-2 flex justify-end"><button className="btn btn-sm btn-primary" onClick={run} disabled={busy}>{busy ? <Spinner /> : null} Import from e-mail</button></div>
    </Card>
  );
}

function PageImport({ opts, onResult }: { opts: Opts; onResult: (r: ImportResult) => void }) {
  const toast = useToast();
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [html, setHtml] = useState("");
  const [url, setUrl] = useState("");
  async function run() {
    if (!file && !html.trim()) { toast.error("Provide a saved HTML file or paste page HTML"); return; }
    setBusy(true);
    try { const r = await api.importPage(file ? { file, url } : { html, url }, opts); onResult(r); toast.success(`Page parsed: ${r.created} created, ${r.updated} updated`); }
    catch (e) { toast.apiError(e, "Page import"); } finally { setBusy(false); }
  }
  return (
    <Card title="Saved ShopGoodwill item page">
      <p className="mb-2 text-xs text-muted">Open the auction in your browser, save the page as HTML (Ctrl/Cmd+S → “Webpage, Complete” or “HTML only”) and upload it. Alternatively paste the page source. The URL helps extract the item ID.</p>
      <Field label="Item URL"><input className="input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://shopgoodwill.com/item/123456" /></Field>
      <input ref={ref} type="file" accept=".html,.htm,text/html" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <div className="mt-2 flex items-center gap-2">
        <button className="btn btn-sm" onClick={() => ref.current?.click()}><FileText size={13} /> Choose HTML file</button>
        <span className="text-xs text-muted">{file ? file.name : "no file selected"}</span>
        {file && <button className="btn btn-xs" onClick={() => { setFile(null); if (ref.current) ref.current.value = ""; }}>clear</button>}
      </div>
      <Field label="…or paste page HTML" className="mt-2"><textarea className="input num" rows={8} value={html} onChange={(e) => setHtml(e.target.value)} disabled={!!file} placeholder="<!doctype html>…" /></Field>
      <div className="mt-2 flex justify-end"><button className="btn btn-sm btn-primary" onClick={run} disabled={busy}>{busy ? <Spinner /> : null} Import page</button></div>
    </Card>
  );
}
