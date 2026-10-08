"use client";
import { ListChecks, Play, RefreshCw, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, relTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { StatusBadge } from "@/components/ui/badges";
import { ApiErrorAlert, EmptyState, Pre, Skeleton, Spinner } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

export default function JobsPage() {
  const toast = useToast();
  const [status, setStatus] = useState("");
  const jobs = useApi(() => api.jobs(status || undefined), [status], { pollMs: 10000 });
  const [busy, setBusy] = useState<number | "process" | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  async function retry(id: number) {
    setBusy(id);
    try { await api.retryJob(id); await jobs.refresh(); toast.info(`Job #${id} re-queued`); }
    catch (e) { toast.apiError(e, "Retry job"); } finally { setBusy(null); }
  }
  async function process() {
    setBusy("process");
    try { const r = await api.processJobs(); await jobs.refresh(); toast.success("Processed pending jobs", JSON.stringify(r.processed)); }
    catch (e) { toast.apiError(e, "Process jobs"); } finally { setBusy(null); }
  }
  const items = jobs.data?.items ?? [];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Background jobs</h1>
          <p className="text-xs text-muted">Analysis, image fetching, e-mail polling and reminder jobs run by the worker. Auto-refreshes every 10 s.</p>
        </div>
        <div className="flex items-center gap-1.5">
          <select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status filter"><option value="">All statuses</option><option value="pending">pending</option><option value="running">running</option><option value="succeeded">succeeded</option><option value="failed">failed</option></select>
          <button className="btn btn-sm" onClick={jobs.refresh}><RefreshCw size={13} className={jobs.refreshing ? "animate-spin" : ""} /></button>
          <button className="btn btn-sm btn-primary" onClick={process} disabled={busy !== null} title="Run pending jobs synchronously now">{busy === "process" ? <Spinner /> : <Play size={13} />} Process pending now</button>
        </div>
      </div>
      {jobs.error && <ApiErrorAlert error={jobs.error} />}
      {jobs.loading && !jobs.data ? <Skeleton className="h-40" /> : items.length === 0 ? (
        <EmptyState icon={<ListChecks size={26} />} title="No jobs">Jobs appear when you import with “queue AI analysis”, run analysis in the background, or the worker polls e-mail.</EmptyState>
      ) : (
        <div className="rounded-lg border border-border bg-elev">
          <table className="tbl">
            <thead><tr><th>#</th><th>Type</th><th>Listing</th><th>Status</th><th className="r">Attempts</th><th>Created</th><th>Finished</th><th>Error</th><th></th></tr></thead>
            <tbody>{items.map((j) => (
              <JobRow key={j.id} j={j} open={open === j.id} onToggle={() => setOpen(open === j.id ? null : j.id)} onRetry={() => retry(j.id)} busy={busy === j.id} />
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function JobRow({ j, open, onToggle, onRetry, busy }: { j: import("@/lib/types").Job; open: boolean; onToggle: () => void; onRetry: () => void; busy: boolean }) {
  return (
    <>
      <tr className="cursor-pointer" onClick={onToggle} tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") onToggle(); }}>
        <td className="num">{j.id}</td>
        <td className="num">{j.job_type}</td>
        <td>{j.listing_id ? <Link href={`/items/${j.listing_id}`} className="text-accent hover:underline" onClick={(e) => e.stopPropagation()}>#{j.listing_id}</Link> : <span className="text-dim">—</span>}</td>
        <td><StatusBadge status={j.status} /></td>
        <td className="r num">{j.attempts}/{j.max_attempts}</td>
        <td className="num whitespace-nowrap text-xs" title={fmtDate(j.created_at)}>{relTime(j.created_at)}</td>
        <td className="num whitespace-nowrap text-xs" title={fmtDate(j.finished_at)}>{j.finished_at ? relTime(j.finished_at) : "—"}</td>
        <td className="max-w-[320px] truncate text-xs text-red" title={j.error ?? ""}>{j.error}</td>
        <td>{(j.status === "failed" || j.status === "succeeded") && <button className="btn btn-xs" onClick={(e) => { e.stopPropagation(); onRetry(); }} disabled={busy}>{busy ? <Spinner size={11} /> : <RotateCcw size={11} />} Retry</button>}</td>
      </tr>
      {open && <tr><td colSpan={9} className="bg-elev-2/40"><div className="grid gap-2 md:grid-cols-2"><div><div className="label">Payload</div><Pre data={j.payload} /></div><div><div className="label">Result</div><Pre data={j.result ?? {}} /></div></div></td></tr>}
    </>
  );
}
