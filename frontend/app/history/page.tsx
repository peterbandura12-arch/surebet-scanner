"use client";

import { useMemo, useState } from "react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  EmptyState,
  ErrorState,
  Label,
  Select,
  SkeletonRows,
} from "@/components/ui/primitives";
import { OpportunityTable } from "@/components/opportunity";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { useLive } from "@/components/providers/live";

export default function HistoryPage() {
  const { lastUpdateAt } = useLive();
  const [status, setStatus] = useState("");
  const [sport, setSport] = useState("");
  const [days, setDays] = useState("14");
  const [sort, setSort] = useState("detected_desc");

  const { data: sports } = useApi(() => backend.sports(), []);
  const params = useMemo(
    () => ({ status, sport, days: Number(days), sort, limit: 500 }),
    [status, sport, days, sort]
  );
  const { data, loading, error } = useApi(
    () => backend.opportunityHistory(params),
    [params],
    { poll: 30000 }
  );

  const items = data?.results ?? [];
  const expiredCount = items.filter((o) => o.status === "expired").length;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="History filters" subtitle={`Persisted opportunities from the simulated demo scan${lastUpdateAt ? " — live" : ""}`} />
        <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <Label>Status</Label>
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="active">Active only</option>
              <option value="expired">Expired only</option>
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
          <div>
            <Label>Period</Label>
            <Select value={days} onChange={(e) => setDays(e.target.value)}>
              <option value="1">Last 24 hours</option>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
            </Select>
          </div>
          <div>
            <Label>Sort</Label>
            <Select value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="detected_desc">Latest detection</option>
              <option value="roi_desc">Highest ROI</option>
              <option value="roi_asc">Lowest ROI</option>
              <option value="start_asc">Event start time</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {error ? <ErrorState message={error} /> : null}

      <Card>
        <CardHeader
          title={`Stored opportunities (${data?.count ?? 0})`}
          right={
            <div className="flex gap-1.5">
              <Badge variant="positive">{items.length - expiredCount} active</Badge>
              <Badge variant="outline">{expiredCount} expired</Badge>
            </div>
          }
        />
        {loading && !data ? (
          <SkeletonRows rows={8} />
        ) : items.length ? (
          <OpportunityTable items={items} />
        ) : (
          <EmptyState
            message="No stored opportunities in this period"
            hint="Keep the backend running — the demo feed persists scans automatically."
          />
        )}
      </Card>
    </div>
  );
}
