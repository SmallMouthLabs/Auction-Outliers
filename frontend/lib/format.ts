const usd0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const usd2 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function money(v: number | null | undefined, opts: { cents?: boolean; dash?: string } = {}): string {
  if (v === null || v === undefined || Number.isNaN(v)) return opts.dash ?? "—";
  return (opts.cents ?? true) ? usd2.format(v) : usd0.format(v);
}

export function pct(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v.toFixed(digits)}%`;
}

export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function conf(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${Math.round(v * 100)}%`;
}

/** Backend timestamps are naive ISO strings in UTC (no "Z"). Normalize before parsing. */
export function parseDate(s: string | null | undefined): Date | null {
  if (!s) return null;
  const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(s);
  const d = new Date(hasTz ? s : `${s}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtDate(s: string | null | undefined, withTime = true): string {
  const d = parseDate(s);
  if (!d) return "—";
  return d.toLocaleString("en-US", withTime
    ? { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }
    : { month: "short", day: "numeric", year: "numeric" });
}

export function relTime(s: string | null | undefined, now = Date.now()): string {
  const d = parseDate(s);
  if (!d) return "—";
  const diff = d.getTime() - now;
  const abs = Math.abs(diff);
  const m = Math.round(abs / 60000);
  const h = Math.round(abs / 3600000);
  const dd = Math.round(abs / 86400000);
  let txt: string;
  if (abs < 45000) txt = "now";
  else if (m < 60) txt = `${m}m`;
  else if (h < 48) txt = `${h}h`;
  else txt = `${dd}d`;
  if (txt === "now") return txt;
  return diff < 0 ? `${txt} ago` : `in ${txt}`;
}

export interface Countdown { text: string; ms: number; urgency: "ended" | "critical" | "soon" | "normal" | "none" }

export function countdown(endsAt: string | null | undefined, now = Date.now()): Countdown {
  const d = parseDate(endsAt);
  if (!d) return { text: "no end", ms: Infinity, urgency: "none" };
  const ms = d.getTime() - now;
  if (ms <= 0) return { text: "ended", ms, urgency: "ended" };
  const s = Math.floor(ms / 1000);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  let text: string;
  if (days > 0) text = `${days}d ${hours}h`;
  else if (hours > 0) text = `${hours}h ${String(mins).padStart(2, "0")}m`;
  else text = `${mins}m ${String(secs).padStart(2, "0")}s`;
  const urgency = ms < 30 * 60000 ? "critical" : ms < 6 * 3600000 ? "soon" : "normal";
  return { text, ms, urgency };
}

export function titleCase(s: string | null | undefined): string {
  if (!s) return "";
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function tierLabel(t: string | null | undefined): string {
  switch (t) {
    case "HIGH_CONFIDENCE": return "High confidence";
    case "SPECULATIVE_HIGH_UPSIDE": return "Speculative upside";
    case "NEEDS_RESEARCH": return "Needs research";
    case "LOW_VALUE": return "Low value";
    default: return t ? titleCase(t) : "Unscored";
  }
}

export function toLocalInputValue(s: string | null | undefined): string {
  const d = parseDate(s);
  if (!d) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromLocalInputValue(v: string): string | null {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function numOrNull(v: string): number | null {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function clamp(n: number, lo: number, hi: number) { return Math.min(hi, Math.max(lo, n)); }
