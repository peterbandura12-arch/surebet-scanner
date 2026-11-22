"use client";

import { useMemo, useState } from "react";
import { FlaskConical, RefreshCw } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Disclaimer,
  EmptyState,
  ErrorState,
  Input,
  Label,
  Select,
  StatCard,
} from "@/components/ui/primitives";
import { PortfolioCurveChart } from "@/components/charts";
import { useApi } from "@/hooks/useApi";
import { backend, ApiError } from "@/lib/api";
import { fmtMoney, fmtSignedPct, fmtTime, outcomeLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function PaperTradingPage() {
  const { data, loading, error, reload } = useApi(() => backend.paper(), [], {
    poll: 20000,
  });
  const { data: opps } = useApi(
    () => backend.opportunityHistory({ status: "active", limit: 50, sort: "roi_desc" }),
    [],
    { poll: 30000 }
  );
  const { data: curve } = useApi(() => backend.analytics.portfolioCurve(), [], {
    poll: 30000,
  });

  const [stake, setStake] = useState("100");
  const [oppId, setOppId] = useState("");
  const [actionMsg, setActionMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [newBankroll, setNewBankroll] = useState("10000");
  const [newName, setNewName] = useState("");

  const defaultOpp = useMemo(() => opps?.results[0]?.id ?? "", [opps]);
  const effectiveOpp = oppId || defaultOpp;

  const place = async () => {
    if (!data || !effectiveOpp) return;
    setActionMsg(null);
    try {
      const pos = await backend.placePosition({
        portfolio_id: data.portfolio.id,
        opportunity_id: effectiveOpp,
        total_stake: parseFloat(stake),
      });
      setActionMsg({
        ok: true,
        text: `Simulated position opened: ${fmtMoney(pos.total_stake)} on ${pos.event_name}. Virtual balance debited.`,
      });
      reload();
    } catch (e) {
      setActionMsg({
        ok: false,
        text: e instanceof ApiError ? e.message : "Placement failed",
      });
    }
  };

  const settle = async () => {
    setActionMsg(null);
    try {
      const res = await backend.settle();
      const n = res.settled.length;
      setActionMsg({
        ok: true,
        text: n
          ? `Settled ${n} simulated position${n === 1 ? "" : "s"}. Profits are virtual.`
          : "No positions due for settlement (events have not started yet).",
      });
      reload();
    } catch (e) {
      setActionMsg({ ok: false, text: e instanceof ApiError ? e.message : "Settlement failed" });
    }
  };

  const createPortfolio = async () => {
    setActionMsg(null);
    try {
      await backend.createPortfolio({
        name: newName || "Virtual Portfolio",
        starting_bankroll: parseFloat(newBankroll) || 10000,
      });
      setActionMsg({ ok: true, text: "Virtual portfolio created (simulated)." });
      setNewName("");
      reload();
    } catch (e) {
      setActionMsg({ ok: false, text: e instanceof ApiError ? e.message : "Creation failed" });
    }
  };

  if (loading && !data) {
    return <div className="h-64 animate-pulse rounded-md bg-surface" />;
  }
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  const s = data.summary;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Virtual balance" value={fmtMoney(data.portfolio.balance)} hint={data.portfolio.name} />
        <StatCard
          label="Simulated P&L"
          value={fmtSignedPct(s.roi_pct)}
          tone={s.total_profit >= 0 ? "positive" : "negative"}
          hint={fmtMoney(s.total_profit)}
        />
        <StatCard label="Open positions" value={s.open_positions} hint={`${s.settled_positions} settled`} />
        <StatCard label="Win / loss" value={`${s.won} / ${s.lost}`} hint={`${fmtMoney(s.total_staked)} total staked`} />
      </div>

      <Disclaimer>
        <span className="inline-flex items-center gap-1.5 font-semibold uppercase tracking-wider">
          <FlaskConical size={12} /> {data.disclaimer}
        </span>
        {" "}Settlement results are drawn from a deterministic simulation of the
        demo odds — they are not real outcomes.
      </Disclaimer>

      {actionMsg ? (
        <div
          className={cn(
            "rounded-md border px-4 py-2.5 text-[13px]",
            actionMsg.ok
              ? "border-accent/30 bg-accent-dim text-accent"
              : "border-risk/30 bg-risk-dim text-risk"
          )}
        >
          {actionMsg.text}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Open a simulated position"
            subtitle="Stakes are split across legs with the same arbitrage engine the scanner uses"
          />
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="sm:col-span-2">
              <Label>Active opportunity</Label>
              <Select value={effectiveOpp} onChange={(e) => setOppId(e.target.value)}>
                {opps?.results.length ? (
                  opps.results.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.event_name} — {o.market_name} ({o.roi_pct.toFixed(2)}%)
                    </option>
                  ))
                ) : (
                  <option value="">No active opportunities right now</option>
                )}
              </Select>
            </div>
            <div>
              <Label>Total stake (€)</Label>
              <Input className="tabular" type="number" min="1" value={stake} onChange={(e) => setStake(e.target.value)} />
            </div>
            <div className="flex gap-2 sm:col-span-3">
              <Button variant="primary" onClick={place} disabled={!effectiveOpp || data.portfolio.balance <= 0}>
                Place simulated bet
              </Button>
              <Button onClick={settle}>
                <RefreshCw size={12} /> Run settlement check
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="New virtual portfolio" subtitle="Reset your simulated bankroll any time" />
          <CardContent className="space-y-3">
            <div>
              <Label>Name</Label>
              <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Semester portfolio" />
            </div>
            <div>
              <Label>Starting bankroll (€)</Label>
              <Input className="tabular" type="number" min="1" value={newBankroll} onChange={(e) => setNewBankroll(e.target.value)} />
            </div>
            <Button className="w-full" onClick={createPortfolio}>Create portfolio</Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader title="Cumulative simulated profit" subtitle="Settled positions only (virtual)" />
        <CardContent>
          {curve?.length ? (
            <PortfolioCurveChart data={curve.map((p) => p.profit)} />
          ) : (
            <EmptyState message="No settled positions yet" hint="Open a position and run a settlement check after kick-off." />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader title={`Positions (${data.positions.length})`} />
        {data.positions.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[840px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                  <th className="px-4 py-2 font-medium">Event</th>
                  <th className="px-3 py-2 font-medium">Market</th>
                  <th className="px-3 py-2 font-medium">Legs (stake)</th>
                  <th className="px-3 py-2 text-right font-medium">Total stake</th>
                  <th className="px-3 py-2 font-medium">Placed</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {data.positions.map((p) => (
                  <tr key={p.id} className="border-b border-line/60 last:border-0">
                    <td className="max-w-[220px] truncate px-4 py-2.5 font-medium">{p.event_name}</td>
                    <td className="px-3 py-2.5 text-dim">{p.market_name}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {p.legs.map((l) => (
                          <span key={l.outcome} className="tabular rounded border border-line bg-raised px-1.5 py-0.5 text-[11px]">
                            {outcomeLabel(l.outcome)} {l.stake.toFixed(2)}€
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="tabular px-3 py-2.5 text-right">{fmtMoney(p.total_stake)}</td>
                    <td className="px-3 py-2.5 text-[12px] text-muted">{fmtTime(p.placed_at)}</td>
                    <td className="px-3 py-2.5">
                      <Badge variant={p.status === "open" ? "positive" : "outline"}>
                        {p.status === "settled" ? `${p.status} · ${p.simulated_result}` : p.status}
                      </Badge>
                    </td>
                    <td
                      className={cn(
                        "tabular px-3 py-2.5 text-right font-semibold",
                        (p.profit ?? 0) > 0 ? "text-accent" : (p.profit ?? 0) < 0 ? "text-risk" : "text-muted"
                      )}
                    >
                      {p.profit === null ? "–" : fmtMoney(p.profit)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No simulated positions yet" hint="Pick an active opportunity above and place a virtual bet." />
        )}
      </Card>
    </div>
  );
}
