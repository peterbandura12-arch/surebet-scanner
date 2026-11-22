"""Paper trading tests: virtual portfolio, positions, simulated settlement.

Everything here is explicitly SIMULATED — no real bets are placed anywhere.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Event, Opportunity, Portfolio, Position
from app.services import paper, scanner
from app.services.paper import PaperTradingError


def _active_opportunity(db) -> Opportunity:
    opp = db.execute(select(Opportunity).where(Opportunity.status == "active")
                     ).scalars().first()
    if opp is None:
        scanner.persist_scan(db, min_roi=0.5)
        opp = db.execute(select(Opportunity).where(Opportunity.status == "active")
                         ).scalars().first()
    assert opp is not None, "demo universe must expose an active opportunity"
    return opp


def _fresh_portfolio(db, bankroll: float = 1000.0) -> Portfolio:
    pf = Portfolio(name=f"test-{bankroll}", starting_bankroll=bankroll,
                   balance=bankroll, currency="EUR", is_simulated=True)
    db.add(pf)
    db.flush()
    return pf


class TestPortfolio:
    def test_get_or_create_defaults(self, db):
        pf = paper.get_or_create_portfolio(db, name="Demo Portfolio")
        assert pf.is_simulated is True
        assert pf.balance == pytest.approx(pf.starting_bankroll)

    def test_get_existing(self, db):
        pf = _fresh_portfolio(db, 750.0)
        assert paper.get_or_create_portfolio(db, portfolio_id=pf.id).id == pf.id

    def test_unknown_portfolio_rejected(self, db):
        with pytest.raises(PaperTradingError):
            paper.get_or_create_portfolio(db, portfolio_id="nope")


class TestPlacePosition:
    def test_place_position(self, db):
        opp = _active_opportunity(db)
        pf = paper.get_or_create_portfolio(db, name="Place", starting_bankroll=1000.0)
        pos = paper.place_position(db, pf.id, opp.id, 100.0)
        assert pos.status == "open"
        assert pos.total_stake == pytest.approx(100.0)
        assert len(pos.legs) == opp.num_outcomes
        stakes = [l["stake"] for l in pos.legs]
        assert sum(stakes) == pytest.approx(100.0, abs=0.02)
        assert all(s >= 0 for s in stakes)
        for leg, src in zip(pos.legs, opp.legs):
            assert leg["outcome"] == src["outcome"]
            assert leg["odds"] == src["odds"]

    def test_balance_debited(self, db):
        opp = _active_opportunity(db)
        pf = _fresh_portfolio(db, 1000.0)
        paper.place_position(db, pf.id, opp.id, 250.0)
        assert pf.balance == pytest.approx(750.0)

    def test_insufficient_balance(self, db):
        opp = _active_opportunity(db)
        pf = _fresh_portfolio(db, 50.0)
        with pytest.raises(PaperTradingError, match="insufficient"):
            paper.place_position(db, pf.id, opp.id, 100.0)

    def test_inactive_opportunity_rejected(self, db):
        opp = _active_opportunity(db)
        pf = paper.get_or_create_portfolio(db, name="Inactive", starting_bankroll=1000.0)
        opp.status = "expired"
        with pytest.raises(PaperTradingError, match="no longer active"):
            paper.place_position(db, pf.id, opp.id, 100.0)
        opp.status = "active"

    def test_unknown_opportunity_rejected(self, db):
        pf = paper.get_or_create_portfolio(db, name="Ghost", starting_bankroll=1000.0)
        with pytest.raises(PaperTradingError, match="not found"):
            paper.place_position(db, pf.id, "missing-opp", 100.0)

    def test_stake_allocation_never_exceeds_stake(self, db):
        opp = _active_opportunity(db)
        pf = paper.get_or_create_portfolio(db, name="Alloc", starting_bankroll=1000.0)
        pos = paper.place_position(db, pf.id, opp.id, 333.33)
        assert sum(l["stake"] for l in pos.legs) <= 333.33 + 1e-6


class TestSettlement:
    def test_settle_due_position(self, db):
        opp = _active_opportunity(db)
        pf = _fresh_portfolio(db, 1000.0)
        pos = paper.place_position(db, pf.id, opp.id, 100.0)
        balance_after_stake = pf.balance
        # nothing due yet (event in the future)
        assert paper.settle_due_positions(db) == []
        assert pos.status == "open"

        ev = db.get(Event, pos.event_id)
        ev.start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)
                         ).replace(tzinfo=None)
        db.flush()
        settled = paper.settle_due_positions(db)
        assert any(e["position_id"] == pos.id for e in settled)
        db.refresh(pos)
        db.refresh(pf)
        assert pos.status == "settled"
        assert pos.simulated_result in ("won", "lost", "void")
        assert pos.payout is not None
        assert pos.profit == pytest.approx(pos.payout - 100.0, abs=0.02)
        assert pf.balance == pytest.approx(balance_after_stake + pos.payout)
        for entry in settled:
            assert "Simulated settlement" in entry["note"]

    def test_settlement_payout_consistency(self, db):
        opp = _active_opportunity(db)
        pf = _fresh_portfolio(db, 2000.0)
        pos = paper.place_position(db, pf.id, opp.id, 120.0)
        ev = db.get(Event, pos.event_id)
        ev.start_time = (datetime.now(timezone.utc) - timedelta(hours=1)
                         ).replace(tzinfo=None)
        db.flush()
        settled = paper.settle_due_positions(db)
        entry = next(e for e in settled if e["position_id"] == pos.id)
        db.refresh(pos)
        winning_leg = next(l for l in pos.legs
                           if l["outcome"] == _winning_outcome(pos, ev))
        assert entry["payout"] == pytest.approx(
            round(winning_leg["stake"] * winning_leg["odds"], 2))


def _winning_outcome(pos: Position, ev: Event) -> str:
    outcomes = [l["outcome"] for l in pos.legs]
    probs = [1.0 / l["odds"] for l in pos.legs]
    return paper.simulate_outcome(pos.id + ev.id, outcomes, probs)


class TestSimulatedOutcome:
    def test_deterministic(self):
        a = paper.simulate_outcome("abcdef12+ev", ["home", "away"])
        b = paper.simulate_outcome("abcdef12+ev", ["home", "away"])
        assert a == b
        assert a in ("home", "away")

    def test_valid_outcomes_with_probs(self):
        for ev in ("aa11", "bb22", "cc33", "dd44"):
            out = paper.simulate_outcome(ev + "+x", ["over", "under"],
                                         [0.7, 0.3])
            assert out in ("over", "under")
