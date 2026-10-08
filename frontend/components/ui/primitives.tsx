"use client";
import { AlertTriangle, Info, Loader2, XCircle } from "lucide-react";
import { useState, type ReactNode } from "react";
import { ApiError } from "@/lib/api";

export function Card({ title, actions, children, className = "", bodyClass = "", id }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; bodyClass?: string; id?: string }) {
  return (
    <section id={id} className={`card ${className}`}>
      {(title || actions) && (
        <header className="card-h">
          <h3 className="card-title">{title}</h3>
          {actions && <div className="flex items-center gap-1.5">{actions}</div>}
        </header>
      )}
      <div className={`card-b ${bodyClass}`}>{children}</div>
    </section>
  );
}

export function Field({ label, children, hint, className = "", htmlFor }: { label: ReactNode; children: ReactNode; hint?: ReactNode; className?: string; htmlFor?: string }) {
  return (
    <div className={className}>
      <label className="label" htmlFor={htmlFor}>{label}</label>
      {children}
      {hint && <div className="mt-1 text-[11px] text-dim">{hint}</div>}
    </div>
  );
}

export function Alert({ kind = "info", title, children, className = "" }: { kind?: "info" | "warning" | "error" | "success"; title?: ReactNode; children?: ReactNode; className?: string }) {
  const map = {
    info: { cls: "border-blue/40 bg-blue/10 text-fg", Icon: Info, ic: "text-blue" },
    warning: { cls: "border-amber/40 bg-amber/10 text-fg", Icon: AlertTriangle, ic: "text-amber" },
    error: { cls: "border-red/40 bg-red/10 text-fg", Icon: XCircle, ic: "text-red" },
    success: { cls: "border-green/40 bg-green/10 text-fg", Icon: Info, ic: "text-green" },
  }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`flex items-start gap-2 rounded-md border px-3 py-2 text-sm ${map.cls} ${className}`}>
      <map.Icon size={15} className={`mt-0.5 shrink-0 ${map.ic}`} />
      <div className="min-w-0 flex-1">
        {title && <div className="font-medium">{title}</div>}
        {children && <div className={title ? "mt-0.5 text-xs text-muted" : ""}>{children}</div>}
      </div>
    </div>
  );
}

/** Inline display of an ApiError with special handling for 424 (provider not configured). */
export function ApiErrorAlert({ error, className = "" }: { error: ApiError | Error | null | undefined; className?: string }) {
  if (!error) return null;
  const e = error instanceof ApiError ? error : null;
  if (e?.isProviderNotConfigured) {
    return (
      <Alert kind="warning" title="AI provider not configured (424)" className={className}>
        <p>{e.message}</p>
        <p className="mt-1">Setup: add <code className="num">ANTHROPIC_API_KEY</code> and/or <code className="num">GEMINI_API_KEY</code> to <code className="num">backend/.env</code>, restart the backend, then retry. Demo listings can be analyzed with the <strong>demo</strong> provider without keys.</p>
      </Alert>
    );
  }
  if (e?.status === 429) return <Alert kind="warning" title="Budget limit reached (429)" className={className}>{e.message}</Alert>;
  if (e?.status === 502) return <Alert kind="error" title="Provider error (502)" className={className}>{e.message}</Alert>;
  if (e?.status === 0) return <Alert kind="error" title="Backend unreachable" className={className}>{e.message}</Alert>;
  return <Alert kind="error" title={e ? `Error ${e.status}` : "Error"} className={className}>{error.message}</Alert>;
}

export function Spinner({ className = "", size = 14 }: { className?: string; size?: number }) {
  return <Loader2 size={size} className={`animate-spin ${className}`} aria-label="Loading" />;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function EmptyState({ icon, title, children, className = "" }: { icon?: ReactNode; title: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-10 text-center ${className}`}>
      {icon && <div className="text-dim">{icon}</div>}
      <div className="text-sm font-medium">{title}</div>
      {children && <div className="max-w-md text-xs text-muted">{children}</div>}
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, className = "" }: { tabs: { id: T; label: ReactNode; count?: number }[]; value: T; onChange: (t: T) => void; className?: string }) {
  return (
    <div role="tablist" className={`flex flex-wrap gap-1 border-b border-border ${className}`}>
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          aria-selected={value === t.id}
          onClick={() => onChange(t.id)}
          className={`-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm transition ${value === t.id ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg"}`}
        >
          {t.label}
          {t.count !== undefined && <span className="num rounded bg-elev-2 px-1 text-[10px] text-muted">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, sub, tone, className = "" }: { label: ReactNode; value: ReactNode; sub?: ReactNode; tone?: "green" | "red" | "amber" | "blue" | "muted"; className?: string }) {
  const color = tone === "green" ? "text-green" : tone === "red" ? "text-red" : tone === "amber" ? "text-amber" : tone === "blue" ? "text-blue" : tone === "muted" ? "text-muted" : "";
  return (
    <div className={`rounded-md border border-border bg-elev-2/60 px-3 py-2 ${className}`}>
      <div className="text-[10.5px] font-medium uppercase tracking-wider text-muted">{label}</div>
      <div className={`num mt-0.5 text-lg font-semibold leading-tight ${color}`}>{value}</div>
      {sub && <div className="mt-0.5 text-[11px] text-dim">{sub}</div>}
    </div>
  );
}

/** Thin horizontal bar (0..1). */
export function Bar({ value, max = 1, tone = "accent", className = "", label }: { value: number; max?: number; tone?: "accent" | "green" | "amber" | "red" | "blue" | "gray"; className?: string; label?: string }) {
  const w = max > 0 ? Math.max(0, Math.min(1, value / max)) * 100 : 0;
  const color = { accent: "bg-accent", green: "bg-green", amber: "bg-amber", red: "bg-red", blue: "bg-blue", gray: "bg-gray" }[tone];
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded bg-elev-2 ${className}`} title={label} aria-label={label}>
      <div className={`h-full ${color}`} style={{ width: `${w}%` }} />
    </div>
  );
}

export function CopyButton({ text, className = "" }: { text: string; className?: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      type="button"
      className={`btn btn-xs ${className}`}
      onClick={async () => { try { await navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1200); } catch { /* ignore */ } }}
      title="Copy to clipboard"
    >
      {ok ? "Copied" : "Copy"}
    </button>
  );
}

export function Toggle({ checked, onChange, label, id }: { checked: boolean; onChange: (v: boolean) => void; label?: ReactNode; id?: string }) {
  return (
    <label className="inline-flex cursor-pointer select-none items-center gap-2 text-sm" htmlFor={id}>
      <input id={id} type="checkbox" className="accent-[var(--accent)]" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}

export function KV({ rows, className = "" }: { rows: [ReactNode, ReactNode][]; className?: string }) {
  return (
    <dl className={`kv ${className}`}>
      {rows.map(([k, v], i) => (
        <div key={i} className="contents">
          <dt>{k}</dt>
          <dd className="min-w-0 break-words">{v ?? <span className="text-dim">—</span>}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Pre({ data, className = "" }: { data: unknown; className?: string }) {
  return <pre className={`scrollbar-thin max-h-72 overflow-auto rounded bg-elev-2 p-2 text-[11px] leading-snug text-muted ${className}`}>{JSON.stringify(data, null, 2)}</pre>;
}
