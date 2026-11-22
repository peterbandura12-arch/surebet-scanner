"use client";

import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Disclaimer,
  ErrorState,
  Input,
  Label,
  Select,
} from "@/components/ui/primitives";
import { backend, ApiError } from "@/lib/api";
import { fmtMoney, fmtPct, outcomeLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

type LegRow = { id: number; outcome: string; odds: string };

let nextId = 4;

export default function CalculatorPage() {
  const [legs, setLegs] = useState<LegRow[]>([
    { id: 1, outcome: "home", odds: "2.10" },
    { id: 2, outcome: "away", odds: "2.05" },
  ]);
  const [bankroll, setBankroll] = useState("1000");
  const [fee, setFee] = useState("0");
  const [step, setStep] = useState("0.5");
  const [rounding, setRounding] = useState("floor");
  const [result, setResult] = useState<null | Awaited<ReturnType<typeof backend.calc>>>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const localS = useMemo(() => {
    const valid = legs.every((l) => parseFloat(l.odds) > 1);
    if (!valid) return null;
    return legs.reduce((acc, l) => acc + 1 / parseFloat(l.odds), 0);
  }, [legs]);

  const canRun =
    legs.filter((l) => l.outcome.trim() && parseFloat(l.odds) > 1).length >= 2 &&
    parseFloat(bankroll) > 0;

  const calculate = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await backend.calc({
        odds: legs
          .filter((l) => l.outcome.trim() && parseFloat(l.odds) > 1)
          .map((l) => ({ outcome: l.outcome.trim(), odds: parseFloat(l.odds) })),
        bankroll: parseFloat(bankroll),
        fee_pct: parseFloat(fee) || 0,
        stake_step: parseFloat(step) || 0.01,
        rounding_mode: rounding,
      });
      setResult(res);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Calculation failed");
    } finally {
      setRunning(false);
    }
  };

  const updateLeg = (id: number, patch: Partial<LegRow>) =>
    setLegs((ls) => ls.map((l) => (l.id === id ? { ...l, ...patch } : l)));

  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <Card className="lg:col-span-2">
        <CardHeader
          title="Inputs"
          subtitle="S = Σ(1/oddsᵢ) — arbitrage when S < 1"
        />
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {legs.map((l, i) => (
              <div key={l.id} className="flex items-center gap-2">
                <span className="w-5 text-center text-xs text-muted">{i + 1}</span>
                <Input
                  className="flex-1"
                  value={l.outcome}
                  placeholder="outcome (e.g. home)"
                  onChange={(e) => updateLeg(l.id, { outcome: e.target.value })}
                />
                <Input
                  className="tabular w-24"
                  type="number"
                  step="0.01"
                  min="1.01"
                  value={l.odds}
                  onChange={(e) => updateLeg(l.id, { odds: e.target.value })}
                />
                <button
                  className="rounded p-1.5 text-muted transition-colors hover:bg-hover hover:text-risk disabled:opacity-30"
                  disabled={legs.length <= 2}
                  onClick={() => setLegs((ls) => ls.filter((x) => x.id !== l.id))}
                  aria-label="Remove leg"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              onClick={() =>
                setLegs((ls) => [
                  ...ls,
                  { id: nextId++, outcome: `outcome_${ls.length + 1}`, odds: "2.00" },
                ])
              }
            >
              <Plus size={12} /> Add leg
            </Button>
            <span className="text-[11px] text-muted">
              Supports 2-way, 3-way and multi-outcome markets
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Bankroll ({`€`})</Label>
              <Input
                className="tabular"
                type="number"
                min="1"
                value={bankroll}
                onChange={(e) => setBankroll(e.target.value)}
              />
            </div>
            <div>
              <Label>Exchange fee %</Label>
              <Input
                className="tabular"
                type="number"
                step="0.1"
                min="0"
                value={fee}
                onChange={(e) => setFee(e.target.value)}
              />
            </div>
            <div>
              <Label>Stake rounding step</Label>
              <Input
                className="tabular"
                type="number"
                step="0.01"
                min="0"
                value={step}
                onChange={(e) => setStep(e.target.value)}
              />
            </div>
            <div>
              <Label>Rounding mode</Label>
              <Select value={rounding} onChange={(e) => setRounding(e.target.value)}>
                <option value="floor">Floor (conservative)</option>
                <option value="nearest">Nearest</option>
              </Select>
            </div>
          </div>

          <Button variant="primary" className="w-full" disabled={!canRun || running} onClick={calculate}>
            {running ? "Calculating…" : "Calculate arbitrage"}
          </Button>

          {localS !== null ? (
            <p className="text-center text-[11px] text-muted">
              S = {localS.toFixed(5)} · margin{" "}
              <span className={localS < 1 ? "text-accent" : "text-risk"}>
                {((localS - 1) * 100).toFixed(2)}%
              </span>
            </p>
          ) : null}

          <Disclaimer>
            Theoretical calculation only. Simulated demo environment — no real
            bets can be placed.
          </Disclaimer>
        </CardContent>
      </Card>

      <div className="space-y-4 lg:col-span-3">
        {error ? <ErrorState message={error} /> : null}
        {!result ? (
          <Card>
            <CardContent className="py-16 text-center text-sm text-muted">
              Enter at least two odds and run the calculation to see the
              optimal stake split, payout and profit.
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader
                title={result.is_arbitrage ? "Arbitrage opportunity" : "No arbitrage"}
                right={
                  <Badge variant={result.is_arbitrage ? "positive" : "negative"}>
                    S = {result.sum_inverse.toFixed(5)}
                  </Badge>
                }
              />
              <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Metric label="Theoretical ROI" value={fmtPct(result.roi_pct)} tone={result.is_arbitrage ? "positive" : "negative"} />
                <Metric label="Total stake" value={fmtMoney(result.total_stake)} />
                <Metric label="Guaranteed payout*" value={fmtMoney(result.guaranteed_payout)} />
                <Metric
                  label="Guaranteed profit"
                  value={fmtMoney(result.guaranteed_profit)}
                  tone={result.guaranteed_profit >= 0 ? "positive" : "negative"}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader title="Stake allocation" subtitle="Payout is equalised across every outcome" />
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                      <th className="px-4 py-2 font-medium">Outcome</th>
                      <th className="px-3 py-2 text-right font-medium">Odds</th>
                      <th className="px-3 py-2 text-right font-medium">Implied prob.</th>
                      <th className="px-3 py-2 text-right font-medium">Stake</th>
                      <th className="px-3 py-2 text-right font-medium">Payout</th>
                      <th className="px-3 py-2 text-right font-medium">Profit if wins</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.legs.map((leg) => (
                      <tr key={leg.outcome} className="border-b border-line/60 last:border-0">
                        <td className="px-4 py-2.5 font-medium">{outcomeLabel(leg.outcome)}</td>
                        <td className="tabular px-3 py-2.5 text-right">{leg.odds.toFixed(2)}</td>
                        <td className="tabular px-3 py-2.5 text-right text-muted">
                          {((1 / leg.odds) * 100).toFixed(2)}%
                        </td>
                        <td className="tabular px-3 py-2.5 text-right font-semibold">
                          {fmtMoney(leg.stake)}
                        </td>
                        <td className="tabular px-3 py-2.5 text-right">{fmtMoney(leg.payout)}</td>
                        <td
                          className={cn(
                            "tabular px-3 py-2.5 text-right font-semibold",
                            leg.payout - result.total_stake >= 0 ? "text-accent" : "text-risk"
                          )}
                        >
                          {fmtMoney(leg.payout - result.total_stake)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {result.notes?.length ? (
                <div className="space-y-1 border-t border-line px-4 py-2.5">
                  {result.notes.map((n) => (
                    <p key={n} className="text-[11px] text-warn">{n}</p>
                  ))}
                </div>
              ) : null}
              <p className="border-t border-line px-4 py-2 text-[10px] text-muted">
                * Payout assumes each leg wins exactly one of the mutually
                exclusive outcomes and the bookmaker settles at shown odds.
              </p>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "positive" | "negative" }) {
  return (
    <div className="rounded-md border border-line bg-raised px-3 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted">{label}</p>
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
