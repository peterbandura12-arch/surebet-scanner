"use client";

import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  EmptyState,
  ErrorState,
  Label,
  Select,
  SkeletonRows,
  StatCard,
} from "@/components/ui/primitives";
import {
  DonutChart,
  HorizontalBarChart,
  OpportunitiesOverTimeChart,
  PortfolioCurveChart,
  RoiDistributionChart,
} from "@/components/charts";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { fmtDuration, fmtPct } from "@/lib/format";

export default function AnalyticsPage() {
  const [days, setDays] = useState("14");
  const [sport, setSport] = useState("");

  const { data: sports } = useApi(() => backend.sports(), []);

  const overTime = useApi(
    () => backend.analytics.opportunitiesOverTime(Number(days), sport),
    [days, sport]
  );
  const distribution = useApi(() => backend.analytics.roiDistribution(), []);
  const bySport = useApi(() => backend.analytics.roiBySport(), []);
  const byBookmaker = useApi(() => backend.analytics.roiByBookmaker(), []);
  const lifetime = useApi(() => backend.analytics.lifetime(), []);
  const detectedVsExpired = useApi(
    () => backend.analytics.detectedVsExpired(Number(days)),
    [days]
  );
  const curve = useApi(() => backend.analytics.portfolioCurve(), []);

  const loading =
    overTime.loading || distribution.loading || bySport.loading;
  const error = overTime.error ?? distribution.error ?? bySport.error;

  const donutData = useMemo(
    () =>
      (detectedVsExpired.data ?? []).map((d) => ({
        name: d.status,
        value: d.count,
      })),
    [detectedVsExpired.data]
  );

  const totalDetected = (detectedVsExpired.data ?? []).reduce(
    (a, d) => a + d.count,
    0
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Analytics filters" subtitle="All series are computed from stored simulated data" />
        <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <Label>Period</Label>
            <Select value={days} onChange={(e) => setDays(e.target.value)}>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
              <option value="180">Last 180 days</option>
            </Select>
          </div>
          <div>
            <Label>Sport</Label>
            <Select value={sport} onChange={(e) => setSport(e.target.value)}>
              <option value="">All</option>
              {sports?.map((s) => (
                <option key={s.key} value={s.key}>{s.name}</option>
              ))}
            </Select>
          </div>
        </CardContent>
      </Card>

      {error ? <ErrorState message={error} /> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Avg opportunity lifetime"
          value={fmtDuration(lifetime.data?.avg_seconds)}
          hint={`${lifetime.data?.count ?? 0} expired tracked`}
        />
        <StatCard
          label="Median lifetime"
          value={fmtDuration(lifetime.data?.median_seconds)}
          hint="From detection to expiry"
        />
        <StatCard
          label={`Detected (${days}d)`}
          value={totalDetected}
        />
        <StatCard
          label="Avg ROI — best sport"
          value={fmtPct(Math.max(0, ...(bySport.data ?? []).map((s) => s.avg_roi)))}
          tone="positive"
          hint="Theoretical, simulated feed"
        />
      </div>

      <Card>
        <CardHeader title={`Opportunities over time (${days}d${sport ? `, ${sport}` : ""})`} />
        <CardContent>
          {loading && !overTime.data ? (
            <div className="h-60 animate-pulse rounded bg-raised" />
          ) : overTime.data?.some((d) => d.count) ? (
            <OpportunitiesOverTimeChart data={overTime.data} height={280} />
          ) : (
            <EmptyState message="No detections in this window" />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="ROI distribution" subtitle="Stored opportunities binned by theoretical ROI" />
          <CardContent>
            {distribution.data?.some((d) => d.count) ? (
              <RoiDistributionChart data={distribution.data} />
            ) : (
              <EmptyState message="No distribution data yet" />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader title="Detected vs expired" subtitle={`Opportunity status counts (${days}d)`} />
          <CardContent>
            {donutData.length ? (
              <DonutChart data={donutData} />
            ) : (
              <EmptyState message="No status data yet" />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader title="Average ROI by sport" />
          <CardContent>
            {bySport.data?.length ? (
              <HorizontalBarChart
                data={bySport.data
                  .slice()
                  .sort((a, b) => b.avg_roi - a.avg_roi)
                  .map((s) => ({ name: s.sport.replace(/_/g, " "), value: s.avg_roi }))}
                dataKey="value"
                nameKey="name"
                valueLabel="Avg ROI %"
                color="#5aa9f5"
              />
            ) : (
              <EmptyState message="No sport data yet" />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader title="Bookmaker participation" subtitle="Legs contributed to detected opportunities" />
          <CardContent>
            {byBookmaker.data?.length ? (
              <HorizontalBarChart
                data={byBookmaker.data.map((b) => ({
                  name: b.bookmaker,
                  value: b.leg_count,
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
          title="Simulated portfolio performance"
          subtitle="Cumulative profit of settled paper-trading positions (simulated)"
        />
        <CardContent>
          {curve.loading && !curve.data ? (
            <div className="h-60 animate-pulse rounded bg-raised" />
          ) : curve.data?.length ? (
            <PortfolioCurveChart data={curve.data.map((p) => p.profit)} />
          ) : (
            <EmptyState
              message="No settled paper positions yet"
              hint="Place a simulated position on the Paper Trading page."
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
