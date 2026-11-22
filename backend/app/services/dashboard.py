"""Dashboard aggregations (all from stored demo data; nothing hardcoded)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (Event, Opportunity, Odds, Portfolio, Sport, Position)


def dashboard_summary(session: Session) -> dict:
    total_opps = session.execute(select(func.count(Opportunity.id))).scalar() or 0
    active_opps = session.execute(
        select(func.count(Opportunity.id)).where(Opportunity.status == "active")).scalar() or 0
    avg_roi = session.execute(
        select(func.avg(Opportunity.roi_pct)).where(Opportunity.status == "active")
    ).scalar() or 0
    max_roi = session.execute(select(func.max(Opportunity.roi_pct))).scalar() or 0
    monitored_events = session.execute(
        select(func.count(Event.id)).where(Event.status == "scheduled")).scalar() or 0
    monitored_sports = session.execute(
        select(func.count(Sport.key))).scalar() or 0

    portfolios = session.execute(select(Portfolio)).scalars().all()
    virtual_capital = sum(p.balance for p in portfolios)

    by_sport = session.execute(
        select(Opportunity.sport_key, func.count(Opportunity.id)).where(
            Opportunity.status == "active").group_by(Opportunity.sport_key)).all()

    legs = session.execute(
        select(Opportunity.legs).where(Opportunity.status == "active")).scalars().all()
    by_bookmaker: dict[str, int] = {}
    for leg_list in legs:
        for leg in leg_list or []:
            bm = leg.get("bookmaker") or "unknown"
            by_bookmaker[bm] = by_bookmaker.get(bm, 0) + 1

    recent = session.execute(
        select(Opportunity).order_by(Opportunity.detected_at.desc()).limit(10)
    ).scalars().all()

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=30)).replace(tzinfo=None)
    movements = session.execute(
        select(Odds).where(Odds.previous_odds.is_not(None),
                           Odds.captured_at >= cutoff)
        .order_by(Odds.captured_at.desc()).limit(15)).scalars().all()
    open_positions = session.execute(
        select(func.count(Position.id)).where(Position.status == "open")).scalar() or 0

    return {
        "demo_mode": True,
        "totals": {
            "opportunities_total": total_opps,
            "opportunities_active": active_opps,
            "avg_active_roi_pct": round(avg_roi, 3),
            "max_roi_pct": round(max_roi, 3),
            "monitored_events": monitored_events,
            "monitored_sports": monitored_sports,
            "virtual_capital": round(virtual_capital, 2),
            "open_positions": open_positions,
        },
        "by_sport": [{"sport": s, "count": c} for s, c in by_sport],
        "by_bookmaker": sorted(
            [{"bookmaker": bm, "count": c} for bm, c in by_bookmaker.items()],
            key=lambda x: -x["count"])[:10],
        "recent_opportunities": [_serialize_opportunity(o) for o in recent],
        "recent_movements": [{
            "event_id": m.event_id, "bookmaker": m.bookmaker_key,
            "market": m.market_key, "outcome": m.outcome,
            "from_odds": m.previous_odds, "to_odds": m.odds,
            "captured_at": m.captured_at.isoformat() if m.captured_at else None,
        } for m in movements],
    }


def _serialize_opportunity(o: Opportunity) -> dict:
    return {
        "id": o.id, "event_name": o.event_name, "league": o.league_name,
        "sport": o.sport_key, "market_key": o.market_key, "market_name": o.market_name,
        "roi_pct": round(o.roi_pct, 3), "status": o.status, "legs": o.legs,
        "detected_at": o.detected_at.isoformat() if o.detected_at else None,
        "start_time": o.start_time.isoformat() if o.start_time else None,
    }
