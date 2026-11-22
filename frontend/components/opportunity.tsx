"use client";

import Link from "next/link";
import { AlertTriangle, ArrowUpRight, X } from "lucide-react";
import { Badge, Button, Card, CardHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";
import {
  fmtAgo,
  fmtMoney,
  fmtOdds,
  fmtPct,
  fmtTime,
  outcomeLabel,
} from "@/lib/format";
import type { Opportunity } from "@/lib/types";

export function RoiBadge({ roi, className }: { roi: number; className?: string }) {
  return (
    <span
      className={cn(
        "tabular inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold",
        roi > 0
          ? "border-accent/30 bg-accent-dim text-accent"
          : "border-risk/30 bg-risk-dim text-risk",
        className
      )}
    >
      {fmtPct(roi)}
    </span>
  );
}

export function LegChips({ opp, compact = false }: { opp: Opportunity; compact?: boolean }) {
  return (
    <div className={cn("flex flex-wrap gap-1.5", compact && "gap-1")}>
      {opp.legs.map((leg) => (
        <span
          key={leg.outcome}
          className="tabular inline-flex items-center gap-1.5 rounded border border-line bg-raised px-1.5 py-0.5 text-[11px]"
          title={`${leg.bookmaker} @ ${leg.odds}`}
        >
          <span className="text-muted">{outcomeLabel(leg.outcome)}</span>
          <span className="font-semibold text-bright">{fmtOdds(leg.odds)}</span>
          <span className="text-[10px] text-muted">{leg.bookmaker}</span>
        </span>
      ))}
    </div>
  );
}

export function OpportunityTable({
  items,
  onOpen,
  showDetected = true,
}: {
  items: Opportunity[];
  onOpen?: (o: Opportunity) => void;
  showDetected?: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] text-left text-[13px]">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
            <th className="px-4 py-2 font-medium">Event</th>
            <th className="px-3 py-2 font-medium">Market</th>
            <th className="px-3 py-2 text-right font-medium">ROI</th>
            <th className="px-3 py-2 text-right font-medium">S</th>
            <th className="px-3 py-2 font-medium">Legs (best odds)</th>
            <th className="px-3 py-2 font-medium">Kick-off</th>
            {showDetected ? (
              <th className="px-3 py-2 font-medium">Detected</th>
            ) : null}
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {items.map((o, i) => (
            <tr
              key={`${o.event_id}-${o.market_key}-${i}`}
              className="border-b border-line/60 transition-colors hover:bg-hover/60"
            >
              <td className="max-w-[260px] px-4 py-2.5">
                <p className="truncate font-medium text-bright">{o.event_name}</p>
                <p className="truncate text-[11px] text-muted">
                  {o.league || o.sport}
                </p>
              </td>
              <td className="px-3 py-2.5 text-dim">{o.market_name}</td>
              <td className="px-3 py-2.5 text-right">
                <RoiBadge roi={o.roi_pct} />
              </td>
              <td className="tabular px-3 py-2.5 text-right text-dim">
                {o.sum_inverse.toFixed(4)}
              </td>
              <td className="max-w-[280px] px-3 py-2.5">
                <LegChips opp={o} compact />
              </td>
              <td className="px-3 py-2.5 text-[12px] text-muted">
                {fmtTime(o.start_time)}
              </td>
              {showDetected ? (
                <td className="px-3 py-2.5 text-[12px] text-muted">
                  {fmtAgo(o.detected_at)}
                </td>
              ) : null}
              <td className="px-3 py-2.5">
                {o.status === "expired" || o.expires_at ? (
                  <Badge variant="outline">expired</Badge>
                ) : o.stale ? (
                  <Badge variant="warn">stale</Badge>
                ) : (
                  <Badge variant="positive">active</Badge>
                )}
              </td>
              <td className="px-3 py-2.5 text-right">
                {onOpen ? (
                  <Button size="sm" variant="ghost" onClick={() => onOpen(o)}>
                    Inspect <ArrowUpRight size={12} />
                  </Button>
                ) : (
                  <Link
                    href={`/scanner?event=${o.event_id}`}
                    className="text-accent/80 hover:text-accent"
                  >
                    <ArrowUpRight size={14} />
                  </Link>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OpportunityDetailModal({
  opp,
  onClose,
}: {
  opp: Opportunity;
  onClose: () => void;
}) {
  const est = opp.estimated;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <Card
        className="mt-10 w-full max-w-2xl"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        <CardHeader
          title={opp.event_name}
          subtitle={`${opp.market_name} · ${opp.league || opp.sport} · starts ${fmtTime(opp.start_time)}`}
          right={
            <button
              onClick={onClose}
              className="rounded p-1 text-muted transition-colors hover:bg-hover hover:text-bright"
              aria-label="Close"
            >
              <X size={15} />
            </button>
          }
        />
        <div className="space-y-4 p-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Arbitrage S" value={opp.sum_inverse.toFixed(5)} />
            <Metric label="Theoretical ROI" value={fmtPct(opp.roi_pct)} tone="positive" />
            <Metric label="Outcomes" value={String(opp.num_outcomes)} />
            <Metric label="Detected" value={fmtAgo(opp.detected_at)} />
          </div>

          <div>
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted">
              Best odds per outcome
            </p>
            <div className="overflow-hidden rounded-md border border-line">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-line bg-raised text-[11px] uppercase tracking-wider text-muted">
                    <th className="px-3 py-1.5 text-left font-medium">Outcome</th>
                    <th className="px-3 py-1.5 text-right font-medium">Odds</th>
                    <th className="px-3 py-1.5 text-right font-medium">Implied prob.</th>
                    <th className="px-3 py-1.5 text-right font-medium">Bookmaker</th>
                    <th className="px-3 py-1.5 text-right font-medium">Quote age</th>
                  </tr>
                </thead>
                <tbody>
                  {opp.legs.map((leg) => (
                    <tr key={leg.outcome} className="border-b border-line/60 last:border-0">
                      <td className="px-3 py-2 font-medium">{outcomeLabel(leg.outcome)}</td>
                      <td className="tabular px-3 py-2 text-right font-semibold text-accent">
                        {fmtOdds(leg.odds)}
                      </td>
                      <td className="tabular px-3 py-2 text-right text-dim">
                        {((1 / leg.odds) * 100).toFixed(2)}%
                      </td>
                      <td className="px-3 py-2 text-right text-dim">{leg.bookmaker}</td>
                      <td className="px-3 py-2 text-right text-[12px] text-muted">
                        {leg.age_seconds !== undefined
                          ? `${Math.round(leg.age_seconds)}s`
                          : fmtAgo(leg.captured_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {opp.validation_notes?.length ? (
            <div className="space-y-1">
              {opp.validation_notes.map((n) => (
                <p key={n} className="flex items-center gap-1.5 text-xs text-warn/90">
                  <AlertTriangle size={12} /> {n}
                </p>
              ))}
            </div>
          ) : null}

          {est ? (
            <div className="rounded-md border border-line bg-raised p-3">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted">
                Estimated allocation for {fmtMoney(est.bankroll)} bankroll (simulated)
              </p>
              <div className="grid gap-x-6 gap-y-1 text-[12px] sm:grid-cols-2">
                {opp.legs.map((leg, i) => (
                  <div key={leg.outcome} className="flex justify-between">
                    <span className="text-muted">{outcomeLabel(leg.outcome)}</span>
                    <span className="tabular text-bright">
                      {fmtMoney(est.stakes[i])}
                    </span>
                  </div>
                ))}
                <div className="flex justify-between border-t border-line pt-1">
                  <span className="text-muted">Total stake</span>
                  <span className="tabular font-semibold">{fmtMoney(est.total_stake)}</span>
                </div>
                <div className="flex justify-between border-t border-line pt-1">
                  <span className="text-muted">Guaranteed profit</span>
                  <span className="tabular font-semibold text-accent">
                    {fmtMoney(est.profit)}
                  </span>
                </div>
              </div>
            </div>
          ) : null}

          {opp.snapshots && opp.snapshots.length > 1 ? (
            <div>
              <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted">
                ROI snapshots
              </p>
              <div className="flex flex-wrap gap-1.5">
                {opp.snapshots.slice(-12).map((s, i) => (
                  <span
                    key={i}
                    className="tabular rounded border border-line bg-raised px-1.5 py-0.5 text-[11px] text-dim"
                    title={s.captured_at}
                  >
                    {fmtPct(s.roi_pct)}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="flex items-center justify-between border-t border-line pt-3">
            <p className="text-[11px] text-muted">
              Simulated demo data. No real bet can be placed from this screen.
            </p>
            <Link href="/paper">
              <Button size="sm" variant="primary">
                Open in Paper Trading
              </Button>
            </Link>
          </div>
        </div>
      </Card>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative";
}) {
  return (
    <div className="rounded-md border border-line bg-raised px-3 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted">
        {label}
      </p>
      <p
        className={cn(
          "tabular mt-0.5 text-sm font-semibold",
          tone === "positive" && "text-accent",
          tone === "negative" && "text-risk"
        )}
      >
        {value}
      </p>
    </div>
  );
}
