"use client";

import Link from "next/link";
import { FlaskConical, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/primitives";
import { useLive } from "@/components/providers/live";

export function Topbar({ title }: { title: string }) {
  const { connected } = useLive();
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-line bg-surface/90 px-4 backdrop-blur md:px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-bright md:hidden">
          SUREBET
        </span>
        <h1 className="hidden text-sm font-semibold text-bright md:block">
          {title}
        </h1>
      </div>
      <div className="flex items-center gap-2.5">
        <span
          className="inline-flex items-center gap-1.5 rounded border border-warn/40 bg-[#191705] px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-warn"
          title="All data on this platform is simulated. No real-money betting is possible."
        >
          <FlaskConical size={11} />
          Demo mode
        </span>
        <Badge variant={connected ? "live" : "outline"}>
          {connected ? <Wifi size={10} /> : <WifiOff size={10} />}
          {connected ? "Live" : "Offline"}
        </Badge>
        <Link
          href="/alerts"
          className="rounded-md px-2 py-1 text-xs text-muted transition-colors hover:bg-hover hover:text-bright"
        >
          Alerts
        </Link>
      </div>
    </header>
  );
}
