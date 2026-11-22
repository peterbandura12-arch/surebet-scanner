from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.core.arbitrage import compute_arbitrage
from app.models import Opportunity, OpportunitySnapshot
from app.services import scanner as scanner_service

router = APIRouter(tags=["scanner"])


@router.get("/scanner")
def run_scan(
    sport: str | None = None,
    league: str | None = None,
    bookmaker: str | None = None,
    min_roi: float | None = Query(None, ge=-10, le=100),
    max_roi: float | None = Query(None, ge=-10, le=100),
    market: str | None = None,
    outcomes: int | None = Query(None, ge=2, le=10),
    status: str = "active",
    sort: str = Query("roi_desc", pattern="^(roi_desc|roi_asc|detected_desc|start_asc|odds_desc)$"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    findings = scanner_service.scan_events(db, min_roi=settings.min_roi_pct)
    results = []
    for f in findings:
        if not f.is_arbitrage:
            continue
        legs = [
            {"outcome": o, "odds": f.best[o]["odds"],
             "bookmaker": f.best[o]["bookmaker"],
             "captured_at": f.best[o]["captured_at"].isoformat(),
             "age_seconds": round(f.best[o]["age_seconds"], 1)}
            for o in f.best
        ]
        results.append({
            "event_id": f.event.id,
            "event_name": f.event.name,
            "league": f.event.league.name if f.event.league else "",
            "sport": f.event.sport_key,
            "market_key": f.market_key,
            "market_name": f.market_name,
            "start_time": f.event.start_time.isoformat() if f.event.start_time else None,
            "roi_pct": round(f.roi_pct, 3),
            "sum_inverse": round(f.sum_inv, 5),
            "num_outcomes": len(legs),
            "legs": legs,
            "stale": bool(f.notes),
            "validation_notes": f.notes,
            "best_odds": max(l["odds"] for l in legs),
            "detected_at": max(l["captured_at"] for l in legs),
        })

    if sport:
        results = [r for r in results if r["sport"] == sport]
    if league:
        results = [r for r in results if league.lower() in r["league"].lower()]
    if bookmaker:
        results = [r for r in results
                   if any(l["bookmaker"] == bookmaker for l in r["legs"])]
    if market:
        results = [r for r in results if r["market_key"] == market]
    if outcomes:
        results = [r for r in results if r["num_outcomes"] == outcomes]
    if min_roi is not None:
        results = [r for r in results if r["roi_pct"] >= min_roi]
    if max_roi is not None:
        results = [r for r in results if r["roi_pct"] <= max_roi]

    sorters = {
        "roi_desc": lambda r: -r["roi_pct"],
        "roi_asc": lambda r: r["roi_pct"],
        "detected_desc": lambda r: r["detected_at"],
        "start_asc": lambda r: r["start_time"] or "",
        "odds_desc": lambda r: -r["best_odds"],
    }
    results.sort(key=sorters[sort])
    return {"simulated": True, "count": len(results),
            "results": results[:limit]}


@router.get("/opportunities")
def opportunities_history(
    status: str | None = Query(None, pattern="^(active|expired)$"),
    sport: str | None = None,
    days: int = Query(14, ge=1, le=365),
    sort: str = Query("detected_desc", pattern="^(roi_desc|roi_asc|detected_desc|start_asc)$"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = select(Opportunity).where(Opportunity.detected_at >= since)
    if status:
        q = q.where(Opportunity.status == status)
    if sport:
        q = q.where(Opportunity.sport_key == sport)
    q = q.order_by(Opportunity.detected_at.desc()).limit(limit)
    rows = db.execute(q).scalars().all()
    items = [scanner_service._serialize(o) for o in rows]
    sorters = {
        "roi_desc": lambda r: -r["roi_pct"],
        "roi_asc": lambda r: r["roi_pct"],
        "detected_desc": lambda r: r["detected_at"] or "",
        "start_asc": lambda r: r["start_time"] or "",
    }
    items.sort(key=sorters[sort])
    return {"simulated": True, "count": len(items), "results": items}


@router.get("/opportunities/{opportunity_id}")
def opportunity_detail(opportunity_id: str, db: Session = Depends(get_db)):
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise HTTPException(404, "opportunity not found")
    snapshots = db.execute(
        select(OpportunitySnapshot)
        .where(OpportunitySnapshot.opportunity_id == opportunity_id)
        .order_by(OpportunitySnapshot.captured_at)).scalars().all()
    data = scanner_service._serialize(opp)
    bankroll = 1000.0
    try:
        calc = compute_arbitrage([l["odds"] for l in opp.legs],
                                 [l["outcome"] for l in opp.legs], bankroll)
        data["estimated"] = {
            "bankroll": bankroll,
            "total_stake": round(calc.total_stake, 2),
            "stakes": [round(l.stake, 2) for l in calc.legs],
            "payout": round(calc.guaranteed_payout, 2),
            "profit": round(calc.guaranteed_profit, 2),
        }
    except Exception:
        data["estimated"] = None
    data["snapshots"] = [{
        "captured_at": s.captured_at.isoformat() if s.captured_at else None,
        "roi_pct": s.roi_pct,
    } for s in snapshots]
    return data
