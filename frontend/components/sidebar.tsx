"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bell,
  BarChart3,
  CalendarDays,
  Calculator,
  Database,
  History,
  LayoutDashboard,
  Percent,
  Radar,
  Settings,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/scanner", label: "Live Scanner", icon: Radar },
  { href: "/events", label: "Sports & Events", icon: CalendarDays },
  { href: "/comparison", label: "Odds Comparison", icon: Percent },
  { href: "/calculator", label: "Surebet Calculator", icon: Calculator },
  { href: "/history", label: "Opportunity History", icon: History },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/paper", label: "Paper Trading", icon: Wallet },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/sources", label: "Data Sources", icon: Database },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-56 flex-col border-r border-line bg-surface md:flex">
      <div className="flex h-14 items-center gap-2.5 border-b border-line px-4">
        <LogoMark />
        <div className="leading-tight">
          <p className="text-[13px] font-bold tracking-wide text-bright">
            SUREBET
          </p>
          <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-muted">
            Scanner
          </p>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {NAV.map(({ href, label, icon: Icon, exact }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] transition-colors duration-150",
                active
                  ? "bg-raised text-bright"
                  : "text-muted hover:bg-hover hover:text-dim"
              )}
            >
              <Icon size={15} strokeWidth={1.8} className={active ? "text-accent" : ""} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-line p-3">
        <div className="flex items-center gap-2 text-[11px] text-muted">
          <Activity size={12} className="text-accent" />
          Simulated demo feed — no real data
        </div>
      </div>
    </aside>
  );
}

export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" fill="none" aria-hidden>
      <rect x="1" y="1" width="24" height="24" rx="4" stroke="#3ddc97" strokeWidth="1.5" />
      <circle cx="13" cy="13" r="5.5" stroke="#3ddc97" strokeWidth="1.5" />
      <line x1="13" y1="1" x2="13" y2="6" stroke="#3ddc97" strokeWidth="1.5" />
      <line x1="13" y1="20" x2="13" y2="25" stroke="#3ddc97" strokeWidth="1.5" />
      <line x1="1" y1="13" x2="6" y2="13" stroke="#3ddc97" strokeWidth="1.5" />
      <line x1="20" y1="13" x2="25" y2="13" stroke="#3ddc97" strokeWidth="1.5" />
      <circle cx="13" cy="13" r="1.6" fill="#3ddc97" />
    </svg>
  );
}

