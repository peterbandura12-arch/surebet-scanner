"use client";

import {
  Activity,
  CalendarDays,
  Layers,
  Radar,
  Target,
  TrendingUp,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  Disclaimer,
  EmptyState,
  ErrorState,
  SkeletonRows,
  StatCard,
} from "@/components/ui/primitives";
import { OpportunitiesOverTimeChart, DonutChart, HorizontalBarChart } from "@/components/charts";
import { OpportunityTable, RoiBadge } from "@/components/opportunity";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { fmtAgo, fmtMoney, fmtOdds, fmtPct, outcomeLabel } from "@/lib/format";

export default function DashboardPage() {
  const { data, loading, error } = useApi(() => backend.dashboard(), [], {
    poll: 15000,
  });
  const { data: overTime } = useApi(
    () => backend.analytics.opportunitiesOverTime(14),
    [],
  );

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-md bg-surface" />
          ))}
        </div>
        <Card>
          <SkeletonRows rows={6} />
        </Card>
      </div>
    );
  }

  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  const t = data.totals;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Opportunities (total)"
          value={t.opportunities_total}
          hint={`${t.opportunities_active} currently active`}
          icon={<Radar size={15} />}
        />
        <StatCard
          label="Avg active ROI"
          value={fmtPct(t.avg_active_roi_pct)}
          tone="positive"
          hint="Theoretical, before fees"
          icon={<TrendingUp size={15} />}
        />
        <StatCard
          label="Peak ROI"
          value={fmtPct(t.max_roi_pct)}
          tone="positive"
          hint="Highest theoretical ever detected"
          icon={<Target size={15} />}
        />
        <StatCard
          label="Monitored events"
          value={t.monitored_events}
          hint={`${t.monitored_sports} sports covered`}
          icon={<CalendarDays size={15} />}
        />
        <StatCard
          label="Virtual capital"
          value={fmtMoney(t.virtual_capital)}
          hint="Paper trading portfolios (simulated)"
          icon={<Wallet size={15} />}
        />
        <StatCard
          label="Open simulated positions"
          value={t.open_positions}
          hint="Paper trades awaiting settlement"
          icon={<Activity size={15} />}
        />
        <StatCard
          label="Bookmakers tracked"
          value={data.by_bookmaker.length}
          hint="Simulated demo bookmakers"
          icon={<Layers size={15} />}
        />
        <StatCard
          label="Data mode"
          value="SIMULATED"
          hint="Demo feeds — never real odds"
          icon={<Activity size={15} />}
        />
      </div>

      <Disclaimer>
        DEMO MODE — every number on this dashboard is computed from a simulated
        odds feed. Nothing here represents real bookmaker odds or real returns.
      </Disclaimer>

      <Card>
        <CardHeader
          title="Opportunities detected — last 14 days"
          subtitle="Aggregated from stored scan history (simulated feed)"
        />
        <CardContent>
          {overTime && overTime.some((d) => d.count > 0) ? (
            <OpportunitiesOverTimeChart data={overTime} />
          ) : (
            <EmptyState
              message="No detection history yet"
              hint="The demo feed populates this chart as it runs."
            />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Active opportunities by sport" />
          <CardContent>
            {data.by_sport.length ? (
              <DonutChart
                data={data.by_sport.map((s) => ({
                  name: s.sport.replace(/_/g, " "),
                  value: s.count,
                }))}
              />
            ) : (
              <EmptyState message="No active opportunities" />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader title="Legs by bookmaker (active opportunities)" />
          <CardContent>
            {data.by_bookmaker.length ? (
              <HorizontalBarChart
                data={data.by_bookmaker.map((b) => ({
                  name: b.bookmaker,
                  value: b.count,
                }))}
                dataKey="value"
                nameKey="name"
                valueLabel="Legs"
              />
            ) : (
              <EmptyState message="No bookmaker data yet" />
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Recent opportunities"
          right={
            <Link href="/scanner" className="text-xs text-accent hover:underline">
              Live scanner →
            </Link>
          }
        />
        {data.recent_opportunities.length ? (
          <OpportunityTable items={data.recent_opportunities.slice(0, 8)} />
        ) : (
          <EmptyState message="No opportunities detected yet" />
        )}
      </Card>

      <Card>
        <CardHeader
          title="Recent odds movements"
          subtitle="Simulated odds drift from the demo feeds"
        />
        {data.recent_movements.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                  <th className="px-4 py-2 font-medium">Event</th>
                  <th className="px-3 py-2 font-medium">Bookmaker</th>
                  <th className="px-3 py-2 font-medium">Market</th>
                  <th className="px-3 py-2 font-medium">Outcome</th>
                  <th className="px-3 py-2 text-right font-medium">From</th>
                  <th className="px-3 py-2 text-right font-medium">To</th>
                  <th className="px-3 py-2 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_movements.map((m, i) => (
                  <tr key={i} className="border-b border-line/60 last:border-0">
                    <td className="max-w-[220px] truncate px-4 py-2 text-dim">
                      {m.event_id.slice(0, 8)}…
                    </td>
                    <td className="px-3 py-2 text-dim">{m.bookmaker}</td>
                    <td className="px-3 py-2 text-dim">{m.market}</td>
                    <td className="px-3 py-2 text-dim">{outcomeLabel(m.outcome)}</td>
                    <td className="tabular px-3 py-2 text-right text-muted">
                      {fmtOdds(m.from_odds)}
                    </td>
                    <td
                      className={`tabular px-3 py-2 text-right font-semibold ${
                        (m.from_odds ?? 0) <= m.to_odds ? "text-accent" : "text-risk"
                      }`}
                    >
                      {fmtOdds(m.to_odds)}
                    </td>
                    <td className="px-3 py-2 text-[12px] text-muted">
                      {fmtAgo(m.captured_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No odds movements in the last 30 minutes" />
        )}
      </Card>
    </div>
  );
}
