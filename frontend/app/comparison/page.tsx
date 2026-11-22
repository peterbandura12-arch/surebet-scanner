"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  EmptyState,
  ErrorState,
  Input,
  Label,
  Select,
  SkeletonRows,
} from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { fmtOdds, fmtTime, outcomeLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { EventItem } from "@/lib/types";

function ComparisonInner() {
  const searchParams = useSearchParams();
  const [sport, setSport] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(
    searchParams.get("event")
  );

  const { data: sports } = useApi(() => backend.sports(), []);
  const { data: evList, loading: loadingList } = useApi(
    () => backend.events({ sport, search, limit: 100 }),
    [sport, search]
  );

  const effectiveId = selected ?? evList?.results[0]?.id ?? null;
  const { data: detail, loading: loadingDetail, error } = useApi(
    () => (effectiveId ? backend.event(effectiveId) : Promise.resolve(null)),
    [effectiveId]
  );
  const { data: movements } = useApi(
    () => (effectiveId ? backend.eventMovements(effectiveId, 40) : Promise.resolve(null)),
    [effectiveId],
    { poll: 20000 }
  );

  const bestPerMarket = useMemo(() => {
    if (!detail) return {};
    const best: Record<string, number> = {};
    for (const m of detail.markets) {
      for (const bm of Object.values(m.bookmakers)) {
        for (const [outcome, o] of Object.entries(bm.odds)) {
          best[`${m.market_key}:${outcome}`] = Math.max(
            best[`${m.market_key}:${outcome}`] ?? 0,
            o.value
          );
        }
      }
    }
    return best;
  }, [detail]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Event odds comparison"
          subtitle="Latest stored odds per simulated bookmaker"
        />
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <div>
            <Label>Sport</Label>
            <Select value={sport} onChange={(e) => setSport(e.target.value)}>
              <option value="">All</option>
              {sports?.map((s) => (
                <option key={s.key} value={s.key}>{s.name}</option>
              ))}
            </Select>
          </div>
          <div className="sm:col-span-3">
            <Label>Event</Label>
            <Select
              value={effectiveId ?? ""}
              onChange={(e) => setSelected(e.target.value)}
            >
              {loadingList && !evList ? <option>Loading…</option> : null}
              {evList?.results.map((e: EventItem) => (
                <option key={e.id} value={e.id}>
                  {e.name} — {e.league || e.sport} ({fmtTime(e.start_time)})
                </option>
              ))}
            </Select>
          </div>
          <div className="sm:col-span-3 lg:col-span-4">
            <Label>Search events</Label>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Type a team name" />
          </div>
        </CardContent>
      </Card>

      {error ? <ErrorState message={error} /> : null}

      {loadingDetail && !detail ? (
        <Card><SkeletonRows rows={6} /></Card>
      ) : detail ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {detail.markets.map((m) => {
              const books = Object.values(m.bookmakers);
              const outcomes = Array.from(
                new Set(books.flatMap((b) => Object.keys(b.odds)))
              );
              return (
                <Card key={m.market_key}>
                  <CardHeader title={m.market_key} subtitle={`${books.length} bookmakers`} />
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-[13px]">
                      <thead>
                        <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                          <th className="px-4 py-2 font-medium">Bookmaker</th>
                          {outcomes.map((o) => (
                            <th key={o} className="px-3 py-2 text-right font-medium">
                              {outcomeLabel(o)}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {books.map((b) => (
                          <tr key={b.bookmaker} className="border-b border-line/60 last:border-0">
                            <td className="px-4 py-2 text-dim">{b.bookmaker}</td>
                            {outcomes.map((o) => {
                              const cell = b.odds[o];
                              const isBest =
                                cell && cell.value === bestPerMarket[`${m.market_key}:${o}`];
                              return (
                                <td
                                  key={o}
                                  className={cn(
                                    "tabular px-3 py-2 text-right font-semibold",
                                    isBest ? "text-accent" : "text-bright"
                                  )}
                                >
                                  {cell ? fmtOdds(cell.value) : "–"}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              );
            })}
          </div>

          <Card>
            <CardHeader
              title="Recent odds movements for this event"
              subtitle="Simulated drift recorded by the demo feeds"
            />
            {movements?.movements.length ? (
              <div className="max-h-72 overflow-y-auto">
                <table className="w-full min-w-[560px] text-left text-[13px]">
                  <thead className="sticky top-0 bg-surface">
                    <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                      <th className="px-4 py-2 font-medium">Bookmaker</th>
                      <th className="px-3 py-2 font-medium">Market</th>
                      <th className="px-3 py-2 font-medium">Outcome</th>
                      <th className="px-3 py-2 text-right font-medium">From</th>
                      <th className="px-3 py-2 text-right font-medium">To</th>
                    </tr>
                  </thead>
                  <tbody>
                    {movements.movements.map((m, i) => (
                      <tr key={i} className="border-b border-line/60 last:border-0">
                        <td className="px-4 py-2 text-dim">{m.bookmaker}</td>
                        <td className="px-3 py-2 text-dim">{m.market}</td>
                        <td className="px-3 py-2 text-muted">{outcomeLabel(m.outcome)}</td>
                        <td className="tabular px-3 py-2 text-right text-muted">{fmtOdds(m.from_odds)}</td>
                        <td
                          className={cn(
                            "tabular px-3 py-2 text-right font-semibold",
                            (m.from_odds ?? 0) <= m.to_odds ? "text-accent" : "text-risk"
                          )}
                        >
                          {fmtOdds(m.to_odds)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState message="No recorded odds movements for this event yet" />
            )}
          </Card>

          {detail.matches.length ? (
            <Card>
              <CardHeader
                title="Provider event matching"
                subtitle="How the two simulated feeds were matched to this event"
              />
              <CardContent className="space-y-2 text-[13px]">
                {detail.matches.map((m) => (
                  <div
                    key={m.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-raised px-3 py-2"
                  >
                    <div className="flex items-center gap-2 text-dim">
                      <span>{m.provider}</span>
                      <span className="text-muted">·</span>
                      <span>{m.external_event_id}</span>
                      {m.manual ? <Badge variant="warn">manual</Badge> : null}
                    </div>
                    <span
                      className={cn(
                        "tabular font-semibold",
                        m.confidence >= 0.82
                          ? "text-accent"
                          : m.confidence >= 0.55
                            ? "text-warn"
                            : "text-risk"
                      )}
                    >
                      {(m.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <p className="text-[11px] text-muted">
            Need the structured event view?{" "}
            <Link href={`/events`} className="text-accent hover:underline">
              Back to Sports &amp; Events
            </Link>
          </p>
        </>
      ) : (
        <EmptyState message="Select an event to compare odds" />
      )}
    </div>
  );
}

export default function ComparisonPage() {
  return (
    <Suspense fallback={<SkeletonRows rows={8} />}>
      <ComparisonInner />
    </Suspense>
  );
}
