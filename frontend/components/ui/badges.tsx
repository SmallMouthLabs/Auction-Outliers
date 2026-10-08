import type { ReactNode } from "react";
import { AlertTriangle, Bot, FlaskConical, User } from "lucide-react";
import { tierLabel, titleCase } from "@/lib/format";
import type { EvidenceQuality, Tier } from "@/lib/types";

export type Tone = "green" | "amber" | "red" | "blue" | "gray" | "purple" | "demo" | "accent";

const toneClass: Record<Tone, string> = {
  green: "bg-green/15 text-green border-green/30",
  amber: "bg-amber/15 text-amber border-amber/30",
  red: "bg-red/15 text-red border-red/30",
  blue: "bg-blue/15 text-blue border-blue/30",
  gray: "bg-gray/15 text-muted border-gray/30",
  purple: "bg-purple/15 text-purple border-purple/30",
  demo: "bg-demo/15 text-demo border-demo/40",
  accent: "bg-accent/15 text-accent border-accent/30",
};

export function Badge({ tone = "gray", children, className = "", title, mono }: { tone?: Tone; children: ReactNode; className?: string; title?: string; mono?: boolean }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-[1px] text-[10.5px] font-semibold uppercase tracking-wide ${mono ? "num" : ""} ${toneClass[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function DemoBadge({ className = "" }: { className?: string }) {
  return <Badge tone="demo" className={className} title="Synthetic demo data - not a real listing"><FlaskConical size={10} /> Demo</Badge>;
}

export function tierTone(t: Tier | string | null | undefined): Tone {
  switch (t) {
    case "HIGH_CONFIDENCE": return "green";
    case "SPECULATIVE_HIGH_UPSIDE": return "amber";
    case "NEEDS_RESEARCH": return "blue";
    case "LOW_VALUE": return "gray";
    default: return "gray";
  }
}

export function TierBadge({ tier, className = "" }: { tier: Tier | string | null | undefined; className?: string }) {
  return <Badge tone={tierTone(tier)} className={className}>{tierLabel(tier)}</Badge>;
}

export function evidenceTone(q: EvidenceQuality | string | null | undefined): Tone {
  switch (q) {
    case "high": return "green";
    case "medium": return "amber";
    case "low": return "red";
    default: return "gray";
  }
}

export function EvidenceBadge({ quality, speculative, className = "" }: { quality: EvidenceQuality | string | null | undefined; speculative?: boolean; className?: string }) {
  if (!quality || quality === "none") return <Badge tone="gray" className={className} title="No sold comparables - valuation unsupported">Unsupported</Badge>;
  return (
    <span className={`inline-flex flex-wrap items-center gap-1 ${className}`}>
      <Badge tone={evidenceTone(quality)} title={`Evidence quality: ${quality}`}>{quality} evid.</Badge>
      {speculative && <Badge tone="amber" title="Valuation is speculative (weak comparables)">Speculative</Badge>}
    </span>
  );
}

export function OriginBadge({ origin, className = "" }: { origin: string | null | undefined; className?: string }) {
  if (origin === "user") return <Badge tone="accent" className={className} title="Identification corrected by you"><User size={10} /> User</Badge>;
  if (origin === "demo") return <Badge tone="demo" className={className} title="Demo fixture output"><FlaskConical size={10} /> Demo</Badge>;
  if (origin === "ai" || origin === "model") return <Badge tone="purple" className={className} title="AI model identification"><Bot size={10} /> AI</Badge>;
  if (!origin) return null;
  return <Badge tone="gray" className={className}>{titleCase(origin)}</Badge>;
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  const tone: Tone = status === "active" ? "green" : status === "ended" || status === "sold" ? "gray" : status === "won" ? "green" : status === "lost" || status === "failed" ? "red" : status === "pending" || status === "running" ? "blue" : status === "succeeded" ? "green" : "gray";
  return <Badge tone={tone}>{status || "unknown"}</Badge>;
}

export function StrengthBadge({ strength }: { strength: string | null | undefined }) {
  const tone: Tone = strength === "strong" ? "red" : strength === "moderate" ? "amber" : "gray";
  return <Badge tone={tone}>{strength || "weak"}</Badge>;
}

export function MisidSignal({ value, className = "" }: { value: number | null | undefined; className?: string }) {
  if (value === null || value === undefined) return <span className="text-dim">—</span>;
  const tone: Tone = value >= 0.6 ? "red" : value >= 0.3 ? "amber" : "gray";
  return (
    <Badge tone={tone} mono className={className} title="Misidentification signal: how strongly the visual evidence disagrees with the seller's description. Raises research priority; does not establish value.">
      {value >= 0.3 && <AlertTriangle size={10} />} {(value * 100).toFixed(0)}
    </Badge>
  );
}

export function ConfidenceBar({ value, className = "" }: { value: number | null | undefined; className?: string }) {
  if (value === null || value === undefined) return <span className="text-dim">—</span>;
  const pctv = Math.round(value * 100);
  const color = pctv >= 75 ? "bg-green" : pctv >= 50 ? "bg-amber" : "bg-red";
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`} title={`Confidence ${pctv}%`}>
      <span className="h-1.5 w-10 overflow-hidden rounded bg-elev-2"><span className={`block h-full ${color}`} style={{ width: `${pctv}%` }} /></span>
      <span className="num text-xs text-muted">{pctv}%</span>
    </span>
  );
}
