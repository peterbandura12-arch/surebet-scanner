"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardHeader,
  EmptyState,
  ErrorState,
  SkeletonRows,
} from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { fmtAgo, fmtOdds, fmtTime, outcomeLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function EventDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { data, loading, error } = useApi(
    () => (id ? backend.event(id) : Promise.resolve(null)),
    [id]
  );
  const { data: movements } = useApi(
    () => (id ? backend.eventMovements(id, 60) : Promise.resolve(null)),
    [id]
  );

  if (loading && !data) return <SkeletonRows rows={8} />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message="Event not found" />;

  const bestPerOutcome: Record<string, number> = {};
  for (const m of data.markets) {
    for (const bm of Object.values(m.bookmakers)) {
      for (const [o, v] of Object.entries(bm.odds)) {
        bestPerOutcome[`${m.market_key}:${o}`] = Math.max(
          bestPerOutcome[`${m.market_key}:${o}`] ?? 0,
          v.value
        );
      }
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title={data.name}
          subtitle={`${data.sport.replace(/_/g, " ")} · ${data.league || "league n/a"} · ${fmtTime(data.start_time)}`}
          right={
            <Link href={`/comparison?event=${data.id}`} className="text-xs text-accent hover:underline">
              Full comparison →
            </Link>
          }
        />
        <CardContent className="grid grid-cols-2 gap-3 text-[13px] sm:grid-cols-4">
          <Field label="Home" value={data.home || "–"} />
          <Field label="Away" value={data.away || "–"} />
          <Field label="Country" value={data.country || "–"} />
          <Field label="Status" value={data.status} />
        </CardContent>
      </Card>

      {data.markets.map((m) => {
        const books = Object.values(m.bookmakers);
        const outcomes = Array.from(new Set(books.flatMap((b) => Object.keys(b.odds))));
        return (
          <Card key={m.market_key}>
            <CardHeader title={m.market_key} subtitle={`${books.length} simulated bookmakers`} />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                    <th className="px-4 py-2 font-medium">Bookmaker</th>
                    {outcomes.map((o) => (
                      <th key={o} className="px-3 py-2 text-right font-medium">{outcomeLabel(o)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {books.map((b) => (
                    <tr key={b.bookmaker} className="border-b border-line/60 last:border-0">
                      <td className="px-4 py-2 text-dim">{b.bookmaker}</td>
                      {outcomes.map((o) => {
                        const cell = b.odds[o];
                        const isBest = cell && cell.value === bestPerOutcome[`${m.market_key}:${o}`];
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

      <Card>
        <CardHeader title="Recent odds movements" />
        {movements?.movements.length ? (
          <div className="max-h-80 overflow-y-auto">
            <table className="w-full min-w-[520px] text-left text-[13px]">
              <thead className="sticky top-0 bg-surface">
                <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                  <th className="px-4 py-2 font-medium">Bookmaker</th>
                  <th className="px-3 py-2 font-medium">Market</th>
                  <th className="px-3 py-2 font-medium">Outcome</th>
                  <th className="px-3 py-2 text-right font-medium">From → To</th>
                </tr>
              </thead>
              <tbody>
                {movements.movements.map((m, i) => (
                  <tr key={i} className="border-b border-line/60 last:border-0">
                    <td className="px-4 py-2 text-dim">{m.bookmaker}</td>
                    <td className="px-3 py-2 text-dim">{m.market}</td>
                    <td className="px-3 py-2 text-muted">{outcomeLabel(m.outcome)}</td>
                    <td className="tabular px-3 py-2 text-right">
                      <span className="text-muted">{fmtOdds(m.from_odds)}</span>
                      {" → "}
                      <span className={cn("font-semibold", (m.from_odds ?? 0) <= m.to_odds ? "text-accent" : "text-risk")}>
                        {fmtOdds(m.to_odds)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No odds movements recorded yet" />
        )}
      </Card>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-raised px-3 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-0.5 font-medium text-bright">{value}</p>
    </div>
  );
}
