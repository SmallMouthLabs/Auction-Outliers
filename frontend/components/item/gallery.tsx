"use client";
import { AlertTriangle, ChevronLeft, ChevronRight, ImageOff, ImagePlus, Link2, Maximize2, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, imageUrl } from "@/lib/api";
import type { ImageOut } from "@/lib/types";
import { DemoBadge } from "@/components/ui/badges";
import { Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

export function Gallery({ listingId, images, index, onIndex, onChanged }: {
  listingId: number;
  images: ImageOut[];
  index: number;
  onIndex: (i: number) => void;
  onChanged: () => Promise<void> | void;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const [showUrls, setShowUrls] = useState(false);
  const [urls, setUrls] = useState("");
  const [lightbox, setLightbox] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const cur = images[index] ?? images[0];
  const curSrc = imageUrl(cur?.url);

  useEffect(() => {
    if (index >= images.length && images.length) onIndex(0);
  }, [images.length, index, onIndex]);

  function step(d: number) {
    if (!images.length) return;
    onIndex((index + d + images.length) % images.length);
  }

  useEffect(() => {
    if (!lightbox) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightbox(false);
      if (e.key === "ArrowRight") step(1);
      if (e.key === "ArrowLeft") step(-1);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lightbox, index, images.length]);

  async function upload(files: FileList | null) {
    if (!files || !files.length) return;
    setBusy("upload");
    try {
      const r = await api.uploadImages(listingId, Array.from(files));
      toast.success(`Uploaded ${r.images.length} photo${r.images.length === 1 ? "" : "s"}`);
      await onChanged();
    } catch (e) { toast.apiError(e, "Photo upload"); } finally { setBusy(null); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function addUrls() {
    const list = urls.split(/\s+/).map((u) => u.trim()).filter((u) => /^https?:\/\//i.test(u));
    if (!list.length) { toast.error("No valid http(s) URLs"); return; }
    setBusy("urls");
    try {
      const r = await api.addImageUrls(listingId, list);
      const failed = r.images.filter((i) => i.fetch_error);
      toast.success(`Added ${r.images.length} image URL${r.images.length === 1 ? "" : "s"}`, failed.length ? `${failed.length} failed to fetch` : undefined);
      setUrls(""); setShowUrls(false);
      await onChanged();
    } catch (e) { toast.apiError(e, "Add image URLs"); } finally { setBusy(null); }
  }

  async function remove() {
    if (!cur) return;
    if (!confirm("Delete this image?")) return;
    setBusy("delete");
    try {
      await api.deleteImage(listingId, cur.id);
      toast.info("Image deleted");
      await onChanged();
    } catch (e) { toast.apiError(e, "Delete image"); } finally { setBusy(null); }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="group relative flex aspect-[4/3] w-full items-center justify-center overflow-hidden rounded-lg border border-border bg-elev-2">
        {curSrc ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={curSrc} alt={`Photo ${index + 1}`} className="max-h-full max-w-full object-contain" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-dim"><ImageOff size={32} /><span className="text-xs">No photos. Upload or add URLs.</span></div>
        )}
        {cur?.is_demo && <DemoBadge className="absolute left-2 top-2" />}
        {cur?.fetch_error && <span className="absolute left-2 bottom-2 flex items-center gap-1 rounded bg-red/80 px-1.5 py-0.5 text-[11px] text-white"><AlertTriangle size={11} /> fetch error: {cur.fetch_error}</span>}
        {images.length > 1 && (
          <>
            <button onClick={() => step(-1)} className="absolute left-1 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-1.5 text-white opacity-0 transition group-hover:opacity-100 focus:opacity-100" aria-label="Previous photo"><ChevronLeft size={18} /></button>
            <button onClick={() => step(1)} className="absolute right-1 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-1.5 text-white opacity-0 transition group-hover:opacity-100 focus:opacity-100" aria-label="Next photo"><ChevronRight size={18} /></button>
          </>
        )}
        {curSrc && (
          <button onClick={() => setLightbox(true)} className="absolute right-2 top-2 rounded bg-black/50 p-1.5 text-white opacity-0 transition group-hover:opacity-100 focus:opacity-100" aria-label="View full size"><Maximize2 size={14} /></button>
        )}
        {images.length > 0 && <span className="num absolute bottom-2 right-2 rounded bg-black/60 px-1.5 py-0.5 text-[11px] text-white">{index + 1}/{images.length}{cur?.width ? ` · ${cur.width}×${cur.height}` : ""}</span>}
      </div>

      {images.length > 0 && (
        <div className="scrollbar-thin flex gap-1.5 overflow-x-auto pb-1">
          {images.map((im, i) => {
            const src = imageUrl(im.url);
            return (
              <button key={im.id} onClick={() => onIndex(i)} className={`relative h-14 w-14 shrink-0 overflow-hidden rounded border transition ${i === index ? "border-accent ring-2 ring-accent/40" : "border-border hover:border-border-strong"}`} aria-label={`Photo ${i + 1}`} title={`#${i} ${im.remote_url || ""}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {src ? <img src={src} alt="" className="h-full w-full object-cover" /> : <ImageOff size={14} className="m-auto text-dim" />}
                <span className="num absolute left-0.5 top-0.5 rounded bg-black/60 px-1 text-[9px] text-white">{i}</span>
                {im.fetch_error && <AlertTriangle size={12} className="absolute bottom-0.5 right-0.5 text-red" />}
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1.5">
        <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => upload(e.target.files)} />
        <button className="btn btn-sm" onClick={() => fileRef.current?.click()} disabled={busy !== null}>{busy === "upload" ? <Spinner /> : <ImagePlus size={13} />} Upload photos</button>
        <button className="btn btn-sm" onClick={() => setShowUrls((v) => !v)}><Link2 size={13} /> Add image URLs</button>
        {cur && <button className="btn btn-sm btn-danger ml-auto" onClick={remove} disabled={busy !== null}><Trash2 size={13} /> Delete</button>}
      </div>
      {showUrls && (
        <div className="flex flex-col gap-1.5 rounded-md border border-border bg-elev-2/60 p-2">
          <textarea className="input" rows={3} placeholder="One image URL per line (http/https)" value={urls} onChange={(e) => setUrls(e.target.value)} />
          <div className="flex justify-end gap-1.5">
            <button className="btn btn-sm" onClick={() => setShowUrls(false)}>Cancel</button>
            <button className="btn btn-sm btn-primary" onClick={addUrls} disabled={busy !== null}>{busy === "urls" ? <Spinner /> : null} Fetch & add</button>
          </div>
        </div>
      )}

      {lightbox && curSrc && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/90 p-6" onClick={() => setLightbox(false)} role="dialog" aria-modal="true">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={curSrc} alt="" className="max-h-full max-w-full object-contain" onClick={(e) => e.stopPropagation()} />
          <button className="absolute right-4 top-4 rounded-full bg-black/60 p-2 text-white" onClick={() => setLightbox(false)} aria-label="Close"><X size={18} /></button>
          {images.length > 1 && (
            <>
              <button onClick={(e) => { e.stopPropagation(); step(-1); }} className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-2 text-white" aria-label="Previous"><ChevronLeft size={22} /></button>
              <button onClick={(e) => { e.stopPropagation(); step(1); }} className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-2 text-white" aria-label="Next"><ChevronRight size={22} /></button>
            </>
          )}
          <span className="num absolute bottom-4 left-1/2 -translate-x-1/2 rounded bg-black/60 px-2 py-1 text-xs text-white">{index + 1} / {images.length} · Esc to close</span>
        </div>
      )}
    </div>
  );
}
