"""Mathematically exact arbitrage (surebet) calculation engine.

For a market with ``n`` mutually exclusive and exhaustive outcomes and the
best available decimal odds ``odds_1..odds_n``:

    S = sum(1 / odds_i)                -> arbitrage exists when S < 1
    ROI = (1 / S - 1) * 100
    Stake_i = B * (1 / odds_i) / S      (stake that equalises payout)

All functions are pure and side-effect free so they can be unit-tested and
reused by the scanner, calculator page and paper-trading simulation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

EPS = 1e-12


class ArbitrageError(ValueError):
    """Base error for invalid arbitrage inputs."""


class InvalidOddsError(ArbitrageError):
    pass


class MissingOddsError(ArbitrageError):
    pass


class IncompatibleMarketError(ArbitrageError):
    pass


@dataclass(frozen=True)
class Leg:
    outcome: str
    bookmaker: str
    odds: float
    implied_probability: float
    stake: float
    raw_stake: float
    payout: float

@dataclass(frozen=True)
class ArbitrageResult:
    is_arbitrage: bool
    sum_inverse: float          # S
    roi_pct: float              # theoretical ROI in %
    total_stake: float
    guaranteed_payout: float
    guaranteed_profit: float
    legs: tuple[Leg, ...]
    fee_pct: float = 0.0
    rounding_dropped: float = 0.0
    worst_case_profit: float = 0.0
    notes: tuple[str, ...] = field(default_factory=tuple)


def validate_odds(odds: list[float] | tuple[float, ...]) -> None:
    """Raise ``InvalidOddsError`` / ``MissingOddsError`` for unusable odds."""
    if odds is None:
        raise MissingOddsError("odds list is missing")
    clean = [o for o in odds if o is not None]
    if len(clean) != len(odds):
        raise MissingOddsError("one or more outcomes have no odds")
    if len(clean) < 2:
        raise MissingOddsError("arbitrage requires at least 2 outcomes")
    if any(isinstance(o, bool) or not isinstance(o, (int, float)) for o in clean):
        raise InvalidOddsError("odds must be numeric")
    if any(math.isnan(o) or math.isinf(o) for o in clean):
        raise InvalidOddsError("odds must be finite")
    if any(o <= 1.0 for o in clean):
        raise InvalidOddsError("decimal odds must be greater than 1.0")


def implied_probabilities(odds: list[float]) -> list[float]:
    validate_odds(odds)
    return [1.0 / o for o in odds]


def sum_inverse(odds: list[float]) -> float:
    return sum(implied_probabilities(odds))


def arbitrage_pct(odds: list[float]) -> float:
    """Positive value => arbitrage exists (market book percentage below 100%)."""
    return (1.0 - sum_inverse(odds)) * 100.0


def theoretical_roi_pct(odds: list[float]) -> float:
    return (1.0 / sum_inverse(odds) - 1.0) * 100.0


def round_stakes(raw_stakes: list[float], total: float, step: float = 0.01,
                 mode: str = "floor") -> tuple[list[float], float]:
    """Round each stake to a bookmaker-acceptable increment without changing
    the total allocation. Returns (rounded_stakes, dropped_amount).

    ``floor``   round every stake down to the step, redistribute remainder.
    ``nearest`` round to the closest step first.
    """
    if not step or step <= 0:
        return list(raw_stakes), 0.0
    if mode not in ("floor", "nearest"):
        raise ArbitrageError(f"unknown rounding mode: {mode!r}")

    if mode == "floor":
        steps = [math.floor(s / step + EPS) for s in raw_stakes]
    else:
        steps = [round(s / step) for s in raw_stakes]

    total_units = int(math.floor(total / step + EPS))
    remaining = total_units - sum(steps)
    if remaining > 0:
        # give leftover units to the legs with the largest rounding shortfall
        order = sorted(range(len(raw_stakes)),
                       key=lambda k: -(steps[k] + 1) * step + raw_stakes[k])
        for k in order[:remaining]:
            steps[k] += 1
    rounded = [max(0, u) * step for u in steps]
    for k, s in enumerate(rounded):
        if raw_stakes[k] > 0 and s == 0.0:
            rounded[k] = step
    dropped = total - sum(rounded)
    return rounded, max(dropped, 0.0)


def compute_arbitrage(
    odds: list[float],
    outcomes: list[str] | tuple[str, ...] | None = None,
    total_bankroll: float = 1000.0,
    fee_pct: float = 0.0,
    stake_step: float = 0.01,
    rounding_mode: str = "floor",
) -> ArbitrageResult:
    """Compute the full arbitrage breakdown for the best odds of each outcome.

    ``odds`` must already be outcome-aligned (one best odds per outcome).
    Raises the typed errors from this module on invalid input.
    """
    validate_odds(odds)
    n = len(odds)
    if outcomes is None:
        outcomes = [f"outcome_{i + 1}" for i in range(n)]
    outcomes = list(outcomes)
    if len(outcomes) != n:
        raise IncompatibleMarketError("outcomes/odds length mismatch")
    if len(set(outcomes)) != n:
        raise IncompatibleMarketError("duplicate outcome names")

    fee = max(0.0, min(float(fee_pct), 50.0)) / 100.0
    bankroll = float(total_bankroll)
    if bankroll <= 0:
        raise ArbitrageError("total bankroll must be positive")

    # exchange-style commission: percentage charged on net winnings per leg,
    # equivalent to reducing each decimal odds o to o - fee * (o - 1)
    eff_odds = [o - fee * (o - 1.0) for o in odds]
    s = sum_inverse(eff_odds)
    raw_stakes = [bankroll * (1.0 / o) / s for o in eff_odds]
    stakes, dropped = round_stakes(raw_stakes, bankroll, step=max(stake_step, 0.0),
                                   mode=rounding_mode)

    legs: list[Leg] = []
    payouts: list[float] = []
    for i, (outcome, stake) in enumerate(zip(outcomes, stakes)):
        payout = stake * eff_odds[i]
        payouts.append(payout)
        legs.append(Leg(outcome=outcome, bookmaker="", odds=odds[i],
                        implied_probability=1.0 / odds[i],
                        stake=stake, raw_stake=raw_stakes[i],
                        payout=payout))

    total_stake = sum(stakes)
    guaranteed_payout = min(payouts) if payouts else 0.0
    profit = guaranteed_payout - total_stake
    roi = (profit / total_stake * 100.0) if total_stake > 0 else 0.0
    roi_theoretical = (1.0 / s - 1.0) * 100.0

    notes: list[str] = []
    if fee > 0:
        notes.append(f"Commission of {fee * 100:.2f}% applied to net winnings per leg.")
    if dropped > (stake_step or 0.0) / 2:
        notes.append(f"{dropped:.2f} of the bankroll could not be allocated due to rounding.")

    return ArbitrageResult(
        is_arbitrage=s < 1.0 - EPS and roi > 0,
        sum_inverse=s,
        roi_pct=roi_theoretical,
        total_stake=total_stake,
        guaranteed_payout=guaranteed_payout,
        guaranteed_profit=profit,
        legs=tuple(legs),
        fee_pct=fee,
        rounding_dropped=dropped,
        worst_case_profit=profit,
        notes=tuple(notes),
    )
