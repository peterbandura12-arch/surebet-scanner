"""Paper trading: virtual portfolio simulation (NO real money, NO real bets).

Stake allocation is computed with the same arbitrage engine used by the
scanner. Settlement of an expired market is simulated by drawing a result
deterministically from the event id + a seeded RNG; results are always
labelled as simulated.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.arbitrage import ArbitrageError, compute_arbitrage
from app.models import (Event, Opportunity, Portfolio, Position)


class PaperTradingError(ValueError):
    pass


def get_or_create_portfolio(session: Session, portfolio_id: str | None = None,
                            name: str = "Demo Portfolio",
                            starting_bankroll: float = 10000.0,
                            currency: str = "EUR") -> Portfolio:
    if portfolio_id:
        pf = session.get(Portfolio, portfolio_id)
        if pf is None:
            raise PaperTradingError("portfolio not found")
        return pf
    pf = session.execute(select(Portfolio).order_by(Portfolio.created_at)).scalars().first()
    if pf is None:
        pf = Portfolio(name=name, starting_bankroll=starting_bankroll,
                       balance=starting_bankroll, currency=currency,
                       is_simulated=True)
        session.add(pf)
        session.flush()
    return pf


def _stakes_for(opp: Opportunity, total_stake: float, fee_pct: float = 0.0) -> list[float]:
    odds = [leg["odds"] for leg in opp.legs]
    outcomes = [leg["outcome"] for leg in opp.legs]
    result = compute_arbitrage(odds, outcomes, total_stake, fee_pct=fee_pct)
    return [leg.stake for leg in result.legs]


def place_position(session: Session, portfolio_id: str, opportunity_id: str,
                   total_stake: float, fee_pct: float = 0.0) -> Position:
    pf = get_or_create_portfolio(session, portfolio_id)
    opp = session.get(Opportunity, opportunity_id)
    if opp is None:
        raise PaperTradingError("opportunity not found")
    if opp.status != "active":
        raise PaperTradingError("opportunity is no longer active")
    if total_stake > pf.balance:
        raise PaperTradingError("insufficient virtual balance")

    try:
        stakes = _stakes_for(opp, total_stake, fee_pct)
    except ArbitrageError as exc:
        raise PaperTradingError(str(exc)) from exc

    pf.balance -= total_stake
    pos = Position(
        portfolio_id=pf.id, opportunity_id=opp.id, event_id=opp.event_id,
        event_name=opp.event_name, market_key=opp.market_key,
        market_name=opp.market_name, sport_key=opp.sport_key,
        legs=[{**leg, "stake": stakes[i]} for i, leg in enumerate(opp.legs)],
        total_stake=total_stake, status="open")
    session.add(pos)
    session.flush()
    return pos


def simulate_outcome(event_id: str, outcomes: list[str],
                     probabilities: list[float] | None = None) -> str:
    """Deterministically simulate a market result from the event id + current
    date. This is a SIMULATION for demo settlement only."""
    day = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
    seed = int(hashlib.sha256(event_id.encode()).hexdigest()[:12], 16) + day
    rng = random.Random(seed)
    if probabilities:
        total = sum(probabilities) or 1.0
        r = rng.random()
        acc = 0.0
        for outcome, p in zip(outcomes, probabilities):
            acc += p / total
            if r <= acc:
                return outcome
        return outcomes[-1]
    return rng.choice(outcomes)


def settle_due_positions(session: Session) -> list[dict]:
    """Settle open positions whose event has started. Profits/payouts are
    simulated from stored odds and a seeded result draw."""
    now = datetime.now(timezone.utc)
    open_pos = session.execute(
        select(Position).where(Position.status == "open")
    ).scalars().all()
    settled = []
    for pos in open_pos:
        event = session.get(Event, pos.event_id) if pos.event_id else None
        start = event.start_time if event else None
        if start and start.tzinfo:
            start = start.replace(tzinfo=None)
        if event is None or (start and start > now.replace(tzinfo=None)):
            continue
        outcomes = [leg["outcome"] for leg in pos.legs]
        probs = [1.0 / leg["odds"] for leg in pos.legs]
        winning = simulate_outcome(pos.id + event.id, outcomes, probs)
        winning_leg = next(leg for leg in pos.legs if leg["outcome"] == winning)
        payout = round(winning_leg["stake"] * winning_leg["odds"], 2)
        profit = round(payout - pos.total_stake, 2)

        pf = session.get(Portfolio, pos.portfolio_id)
        if pf is not None:
            pf.balance = round(pf.balance + payout, 2)

        pos.status = "settled"
        pos.simulated_result = "won" if profit > 0 else ("void" if abs(profit) < 0.01 else "lost")
        pos.payout = payout
        pos.profit = profit
        pos.settled_at = now
        settled.append({
            "position_id": pos.id, "event": pos.event_name,
            "simulated_result": pos.simulated_result,
            "payout": payout, "profit": profit,
            "note": "Simulated settlement (demo). No real bet was placed.",
        })
    if settled:
        session.flush()
    return settled


def serialize_position(pos: Position) -> dict:
    return {
        "id": pos.id,
        "portfolio_id": pos.portfolio_id,
        "event_name": pos.event_name,
        "market_key": pos.market_key,
        "market_name": pos.market_name,
        "sport": pos.sport_key,
        "legs": pos.legs,
        "total_stake": pos.total_stake,
        "status": pos.status,
        "payout": pos.payout,
        "profit": pos.profit,
        "simulated_result": pos.simulated_result,
        "placed_at": pos.placed_at.isoformat() if pos.placed_at else None,
        "settled_at": pos.settled_at.isoformat() if pos.settled_at else None,
    }


def serialize_portfolio(pf: Portfolio) -> dict:
    return {
        "id": pf.id,
        "name": pf.name,
        "currency": pf.currency,
        "starting_bankroll": pf.starting_bankroll,
        "balance": round(pf.balance, 2),
        "is_simulated": pf.is_simulated,
    }
