"use client";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import { ApiError } from "@/lib/api";

type Kind = "success" | "error" | "info" | "warning";
interface Toast { id: number; kind: Kind; title: string; detail?: string; sticky?: boolean }

interface ToastCtx {
  push: (t: Omit<Toast, "id">) => void;
  success: (title: string, detail?: string) => void;
  error: (title: string, detail?: string) => void;
  info: (title: string, detail?: string) => void;
  /** Show an API error (preserves backend `detail`). */
  apiError: (e: unknown, context?: string) => void;
}

const Ctx = createContext<ToastCtx | null>(null);

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return String(e);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const remove = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev.slice(-4), { ...t, id }]);
    if (!t.sticky) setTimeout(() => remove(id), t.kind === "error" ? 9000 : 4500);
  }, [remove]);
  const value = useMemo<ToastCtx>(() => ({
    push,
    success: (title, detail) => push({ kind: "success", title, detail }),
    error: (title, detail) => push({ kind: "error", title, detail }),
    info: (title, detail) => push({ kind: "info", title, detail }),
    apiError: (e, context) => {
      const msg = errorMessage(e);
      const status = e instanceof ApiError ? e.status : undefined;
      const title = context ? `${context} failed${status ? ` (${status})` : ""}` : `Request failed${status ? ` (${status})` : ""}`;
      push({ kind: status === 424 ? "warning" : "error", title, detail: msg, sticky: status === 424 });
    },
  }), [push]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-3 top-3 z-[100] flex w-[380px] max-w-[calc(100vw-24px)] flex-col gap-2">
        {toasts.map((t) => <ToastView key={t.id} t={t} onClose={() => remove(t.id)} />)}
      </div>
    </Ctx.Provider>
  );
}

function ToastView({ t, onClose }: { t: Toast; onClose: () => void }) {
  const Icon = t.kind === "success" ? CheckCircle2 : t.kind === "error" ? XCircle : t.kind === "warning" ? AlertTriangle : Info;
  const color = t.kind === "success" ? "text-green" : t.kind === "error" ? "text-red" : t.kind === "warning" ? "text-amber" : "text-blue";
  return (
    <div role="status" className="pointer-events-auto fade-in flex items-start gap-2 rounded-md border border-border-strong bg-elev p-3 shadow-lg shadow-black/30">
      <Icon size={16} className={`mt-0.5 shrink-0 ${color}`} />
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium">{t.title}</div>
        {t.detail && <div className="mt-0.5 break-words text-xs text-muted">{t.detail}</div>}
      </div>
      <button onClick={onClose} className="btn btn-ghost btn-xs -mr-1 -mt-1" aria-label="Dismiss"><X size={13} /></button>
    </div>
  );
}

export function useToast(): ToastCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useToast outside ToastProvider");
  return c;
}
