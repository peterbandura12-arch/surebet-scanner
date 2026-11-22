from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.system import rate_limit
from app.db import get_db
from app.models import Position, Portfolio
from app.schemas import CalcRequest, PaperPlaceRequest, PortfolioCreate
from app.services import paper
from app.core.arbitrage import compute_arbitrage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["paper trading", "calculator"])


@router.get("/paper/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    pf = paper.get_or_create_portfolio(db)
    positions = db.execute(
        select(Position).where(Position.portfolio_id == pf.id)
        .order_by(Position.placed_at.desc())).scalars().all()
    settled = [p for p in positions if p.status == "settled"]
    won = [p for p in settled if (p.profit or 0) > 0]
    lost = [p for p in settled if (p.profit or 0) <= 0]
    return {
        "simulated": True,
        "portfolio": paper.serialize_portfolio(pf),
        "summary": {
            "open_positions": len(positions) - len(settled),
            "settled_positions": len(settled),
            "won": len(won),
            "lost": len(lost),
            "total_profit": round(sum(p.profit or 0 for p in settled), 2),
            "total_staked": round(sum(p.total_stake for p in settled), 2),
            "roi_pct": round(
                (sum(p.profit or 0 for p in settled) /
                 max(sum(p.total_stake for p in settled), 0.01)) * 100, 3),
        },
        "positions": [paper.serialize_position(p) for p in positions[:200]],
        "disclaimer": ("Virtual portfolio. Results are SIMULATED and do not "
                       "represent real financial performance."),
    }


@router.post("/paper/portfolios", dependencies=[Depends(rate_limit())])
def create_portfolio(body: PortfolioCreate, db: Session = Depends(get_db)):
    pf = Portfolio(name=body.name, currency=body.currency,
                   starting_bankroll=body.starting_bankroll,
                   balance=body.starting_bankroll, is_simulated=True)
    db.add(pf)
    db.commit()
    return paper.serialize_portfolio(pf)


@router.post("/paper/positions", dependencies=[Depends(rate_limit())])
def place_position(body: PaperPlaceRequest, db: Session = Depends(get_db)):
    try:
        pos = paper.place_position(db, body.portfolio_id, body.opportunity_id,
                                   body.total_stake)
        db.commit()
    except paper.PaperTradingError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    return paper.serialize_position(pos)


@router.post("/paper/settle", dependencies=[Depends(rate_limit())])
def settle_positions(db: Session = Depends(get_db)):
    settled = paper.settle_due_positions(db)
    db.commit()
    return {"simulated": True, "settled": settled}


@router.post("/calc")
def calculator(body: CalcRequest):
    """Stateless surebet calculator. Pure math, no data fabrication."""
    odds = [l.odds for l in body.odds]
    outcomes = [l.outcome for l in body.odds]
    try:
        r = compute_arbitrage(odds, outcomes, body.bankroll,
                              fee_pct=body.fee_pct,
                              stake_step=body.stake_step,
                              rounding_mode=body.rounding_mode)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return {
        "simulated": None,
        "is_arbitrage": r.is_arbitrage,
        "sum_inverse": round(r.sum_inverse, 6),
        "arbitrage_margin_pct": round((1 - r.sum_inverse) * 100, 4),
        "roi_pct": round(r.roi_pct, 4),
        "total_stake": round(r.total_stake, 2),
        "guaranteed_payout": round(r.guaranteed_payout, 2),
        "guaranteed_profit": round(r.guaranteed_profit, 2),
        "rounding_dropped": round(r.rounding_dropped, 4),
        "notes": list(r.notes),
        "legs": [{
            "outcome": l.outcome, "odds": l.odds,
            "implied_probability": round(l.implied_probability, 6),
            "stake": round(l.stake, 2), "payout": round(l.payout, 2),
        } for l in r.legs],
    }
