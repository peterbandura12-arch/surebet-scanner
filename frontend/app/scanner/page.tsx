"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { RefreshCw } from "lucide-react";
import {
  Badge,
  Button,
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
import {
  OpportunityDetailModal,
  OpportunityTable,
  RoiBadge,
} from "@/components/opportunity";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { useLive } from "@/components/providers/live";
import { fmtAgo, fmtPct } from "@/lib/format";
import type { Opportunity } from "@/lib/types";

function ScannerInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { lastUpdate, lastUpdateAt, connected } = useLive();

  const [sport, setSport] = useState("");
  const [league, setLeague] = useState("");
  const [bookmaker, setBookmaker] = useState("");
  const [market, setMarket] = useState("");
  const [outcomes, setOutcomes] = useState("");
  const [minRoi, setMinRoi] = useState("");
  const [maxRoi, setMaxRoi] = useState("");
  const [sort, setSort] = useState("roi_desc");
  const [detail, setDetail] = useState<Opportunity | null>(null);

  const { data: sports } = useApi(() => backend.sports(), []);
  const { data: books } = useApi(() => backend.bookmakers(), []);
  const { data: markets } = useApi(
    () => backend.sportMarkets(sport || "football"),
    [sport]
  );

  const filters = useMemo(
    () => ({
      sport,
      league,
      bookmaker,
      market,
      outcomes,
      min_roi: minRoi,
      max_roi: maxRoi,
      sort,
      limit: 200,
    }),
    [sport, league, bookmaker, market, outcomes, minRoi, maxRoi, sort]
  );

  const { data, loading, error, reload } = useApi(
    () => backend.scanner(filters),
    [filters],
    { poll: 20000 }
  );

  const openEventFromUrl = useCallback(
    async (eventId: string | null) => {
      if (!eventId || !data) return;
      const match = data.results.find((o) => o.event_id === eventId);
      if (match) setDetail(match);
    },
    [data]
  );

  useEffect(() => {
    openEventFromUrl(searchParams.get("event"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const refreshClicked = () => {
    reload();
    router.replace("/scanner");
  };

  const results = data?.results ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge variant="warn">Simulated feed</Badge>
          {connected ? (
            <span className="text-[11px] text-muted">
              WebSocket live · last scan {fmtAgo(lastUpdateAt ? new Date(lastUpdateAt).toISOString() : null)}
            </span>
          ) : (
            <span className="text-[11px] text-muted">
              REST polling — WS offline
            </span>
          )}
        </div>
        <Button size="sm" onClick={refreshClicked}>
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader
          title="Filters"
          subtitle="Scan runs server-side against the freshest stored odds snapshot"
        />
        <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
          <div>
            <Label>Sport</Label>
            <Select value={sport} onChange={(e) => { setSport(e.target.value); setMarket(""); }}>
              <option value="">All</option>
              {sports?.map((s) => (
                <option key={s.key} value={s.key}>{s.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>League</Label>
            <Input value={league} onChange={(e) => setLeague(e.target.value)} placeholder="e.g. Premier" />
          </div>
          <div>
            <Label>Bookmaker</Label>
            <Select value={bookmaker} onChange={(e) => setBookmaker(e.target.value)}>
              <option value="">All</option>
              {books?.map((b) => (
                <option key={b.key} value={b.name}>{b.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Market</Label>
            <Select value={market} onChange={(e) => setMarket(e.target.value)}>
              <option value="">All</option>
              {markets?.map((m) => (
                <option key={m.key} value={m.key}>{m.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Outcomes</Label>
            <Select value={outcomes} onChange={(e) => setOutcomes(e.target.value)}>
              <option value="">Any</option>
              <option value="2">2-way</option>
              <option value="3">3-way</option>
            </Select>
          </div>
          <div>
            <Label>Min ROI %</Label>
            <Input type="number" step="0.1" value={minRoi} onChange={(e) => setMinRoi(e.target.value)} placeholder="0.5" />
          </div>
          <div>
            <Label>Max ROI %</Label>
            <Input type="number" step="0.1" value={maxRoi} onChange={(e) => setMaxRoi(e.target.value)} placeholder="—" />
          </div>
          <div>
            <Label>Sort by</Label>
            <Select value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="roi_desc">Highest ROI</option>
              <option value="roi_asc">Lowest ROI</option>
              <option value="detected_desc">Latest detection</option>
              <option value="start_asc">Event start time</option>
              <option value="odds_desc">Best available odds</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {lastUpdate?.new?.length ? (
        <Card className="border-accent/30">
          <CardContent className="flex items-center gap-3 py-2.5 text-[13px]">
            <Badge variant="positive">New</Badge>
            <span className="text-dim">
              {lastUpdate.new.length} new opportunit
              {lastUpdate.new.length === 1 ? "y" : "ies"} detected by the last
              simulated scan tick
              {lastUpdate.new[0] ? (
                <> — best: <span className="font-medium text-bright">
                  {lastUpdate.new[0].event_name} <RoiBadge roi={lastUpdate.new[0].roi_pct} className="ml-1" />
                </span></>
              ) : null}
            </span>
          </CardContent>
        </Card>
      ) : null}

      {error ? <ErrorState message={error} /> : null}

      <Card>
        <CardHeader
          title={`Arbitrage opportunities (${data?.count ?? 0})`}
          subtitle="S < 1.00 with theoretical ROI above the configured floor"
        />
        {loading && !data ? (
          <SkeletonRows rows={8} />
        ) : results.length ? (
          <OpportunityTable items={results} onOpen={setDetail} />
        ) : (
          <EmptyState
            message="No active surebets match the current filters"
            hint="The simulated feed moves odds every few seconds — retry shortly."
          />
        )}
      </Card>

      {detail ? (
        <OpportunityDetailPanel
          opp={detail}
          onClose={() => {
            setDetail(null);
            router.replace("/scanner");
          }}
        />
      ) : null}
    </div>
  );
}

function OpportunityDetailPanel({
  opp,
  onClose,
}: {
  opp: Opportunity;
  onClose: () => void;
}) {
  const { data } = useApi(
    () => (opp.id ? backend.opportunity(opp.id) : Promise.resolve(opp)),
    [opp.id]
  );
  return <OpportunityDetailModal opp={data ?? opp} onClose={onClose} />;
}

export default function LiveScannerPage() {
  return (
    <Suspense fallback={<SkeletonRows rows={8} />}>
      <ScannerInner />
    </Suspense>
  );
}
