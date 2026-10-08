"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, BookOpen, Bookmark, FlaskConical, LayoutDashboard, ListChecks, Settings, Upload } from "lucide-react";
import type { ReactNode } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { StatusBar } from "./status-bar";

const NAV = [
  { href: "/", label: "Opportunities", icon: LayoutDashboard },
  { href: "/watchlist", label: "Watchlist", icon: Bookmark },
  { href: "/import", label: "Import", icon: Upload },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/reference", label: "Reference", icon: BookOpen },
  { href: "/jobs", label: "Jobs", icon: ListChecks },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const status = useApi(() => api.status(), [], { pollMs: 30000 });
  const demoCount = status.data?.counts.demo_listings ?? 0;

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-[184px] shrink-0 flex-col border-r border-border bg-elev md:flex">
        <Link href="/" className="flex items-center gap-2 border-b border-border px-4 py-3">
          <span className="flex h-6 w-6 items-center justify-center rounded bg-accent text-accent-fg"><Activity size={14} /></span>
          <span className="text-sm font-bold tracking-[0.18em]">OUTLIER</span>
        </Link>
        <nav className="flex flex-1 flex-col gap-0.5 p-2" aria-label="Main">
          {NAV.map((n) => {
            const active = n.href === "/" ? pathname === "/" || pathname.startsWith("/items") : pathname.startsWith(n.href);
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition ${active ? "bg-accent/15 text-fg" : "text-muted hover:bg-hover hover:text-fg"}`}
                aria-current={active ? "page" : undefined}
              >
                <n.icon size={15} className={active ? "text-accent" : ""} />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-border px-3 py-2 text-[10.5px] text-dim">
          <div>Auction intelligence & sourcing</div>
          <div className="num">API {status.data?.version ?? "…"}</div>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <StatusBar status={status.data} error={status.error} loading={status.loading} onRefresh={status.refresh} />
        {demoCount > 0 && (
          <div className="flex items-center gap-2 border-b border-demo/40 bg-demo/10 px-4 py-1.5 text-xs text-fg">
            <FlaskConical size={13} className="text-demo" />
            <span><strong>DEMO MODE:</strong> {demoCount} synthetic demo listing{demoCount === 1 ? "" : "s"} loaded. Rows marked <span className="font-semibold text-demo">DEMO</span> are fixtures, not real auctions; AI outputs on them are canned.</span>
          </div>
        )}
        <main className="min-w-0 flex-1 px-4 py-4">{children}</main>
      </div>
    </div>
  );
}
