"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";

const TITLES: [string, string][] = [
  ["/scanner", "Live Scanner"],
  ["/events", "Sports & Events"],
  ["/comparison", "Odds Comparison"],
  ["/calculator", "Surebet Calculator"],
  ["/history", "Opportunity History"],
  ["/analytics", "Analytics"],
  ["/paper", "Paper Trading"],
  ["/alerts", "Alerts & Notifications"],
  ["/sources", "Data Sources"],
  ["/settings", "Settings"],
];

function titleFor(pathname: string): string {
  const match = TITLES.find(([prefix]) => pathname.startsWith(prefix));
  return match ? match[1] : "Dashboard";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen">
      <Sidebar />
      <div className="md:pl-56">
        <Topbar title={titleFor(pathname)} />
        <main className="mx-auto max-w-[1400px] px-4 py-5 md:px-6">{children}</main>
        <footer className="border-t border-line px-6 py-4 text-center text-[11px] text-muted">
          SUREBET SCANNER — demo build. All odds, opportunities and portfolio
          results are <span className="text-warn">simulated</span>. No real-money
          betting is possible.
        </footer>
      </div>
    </div>
  );
}
