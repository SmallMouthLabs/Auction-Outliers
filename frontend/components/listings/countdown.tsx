"use client";
import { Clock } from "lucide-react";
import { countdown, fmtDate } from "@/lib/format";
import { useNow } from "@/lib/useApi";

export function Countdown({ endsAt, className = "", showIcon = true }: { endsAt: string | null | undefined; className?: string; showIcon?: boolean }) {
  const now = useNow(1000);
  const c = countdown(endsAt, now);
  const color = c.urgency === "critical" ? "text-red" : c.urgency === "soon" ? "text-amber" : c.urgency === "ended" ? "text-dim" : "text-fg";
  return (
    <span className={`num inline-flex items-center gap-1 whitespace-nowrap ${color} ${className}`} title={endsAt ? `Ends ${fmtDate(endsAt)}` : "No end time"}>
      {showIcon && <Clock size={11} className="opacity-70" />}
      {c.text}
    </span>
  );
}
