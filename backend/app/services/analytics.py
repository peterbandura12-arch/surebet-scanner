"""Analytics aggregations (all computed from stored demo data)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Opportunity, Odds, Position


def opportunities_over_time(session: Session, days: int = 14, sport: str | None = None) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = select(Opportunity.detected_at, Opportunity.roi_pct).where(
        Opportunity.detected_at >= since)
    if sport:
        q = q.where(Opportunity.sport_key == sport)
    rows = session.execute(q).all()
    buckets: dict[str, dict] = {}
    for i in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date().isoformat()
        buckets[day] = {"date": day, "count": 0, "avg_roi": None, "rois": []}
    for detected_at, roi in rows:
        day = detected_at.date().isoformat() if detected_at else None
        if day in buckets:
            buckets[day]["count"] += 1
            buckets[day]["rois"].append(roi)
    out = []
    for b in buckets.values():
        rois = b.pop("rois")
        b["avg_roi"] = round(sum(rois) / len(rois), 3) if rois else None
        out.append(b)
    return out


def roi_distribution(session: Session, min_roi: float = 0.5) -> list[dict]:
    rows = session.execute(select(Opportunity.roi_pct)).scalars().all()
    bins = [(0.5, 1), (1, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 10), (10, 100)]
    out = [{"label": f"{lo}–{hi}%", "count": 0} for lo, hi in bins]
    for roi in rows:
        if roi is None or roi < min_roi:
            continue
        for i, (lo, hi) in enumerate(bins):
            if lo <= roi < hi:
                out[i]["count"] += 1
                break
    return out


def roi_by_sport(session: Session) -> list[dict]:
    rows = session.execute(
        select(Opportunity.sport_key, func.count(Opportunity.id),
               func.avg(Opportunity.roi_pct))
        .group_by(Opportunity.sport_key)).all()
    return [{"sport": s, "count": c, "avg_roi": round(a or 0, 3)} for s, c, a in rows]


def roi_by_bookmaker(session: Session) -> list[dict]:
    legs = session.execute(select(Opportunity.legs)).scalars().all()
    stats: dict[str, dict] = {}
    for leg_list in legs:
        for leg in leg_list or []:
            bm = leg.get("bookmaker") or "unknown"
            st = stats.setdefault(bm, {"count": 0, "odds_sum": 0.0})
            st["count"] += 1
            st["odds_sum"] += leg.get("odds", 0)
    out = []
    for bm, st in sorted(stats.items(), key=lambda kv: -kv[1]["count"]):
        out.append({"bookmaker": bm, "leg_count": st["count"],
                    "avg_best_odds": round(st["odds_sum"] / max(st["count"], 1), 3)})
    return out[:15]


def opportunity_lifetime(session: Session) -> dict:
    rows = session.execute(
        select(Opportunity.detected_at, Opportunity.expires_at)
        .where(Opportunity.status == "expired",
               Opportunity.detected_at.is_not(None),
               Opportunity.expires_at.is_not(None))).all()
    lifetimes = [(e - d).total_seconds() for d, e in rows]
    n = len(lifetimes)
    if n == 0:
        return {"count": 0, "avg_seconds": None, "median_seconds": None}
    lifetimes.sort()
    return {
        "count": n,
        "avg_seconds": round(sum(lifetimes) / n, 1),
        "median_seconds": lifetimes[n // 2],
    }


def detected_vs_expired(session: Session, days: int = 14) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = session.execute(
        select(Opportunity.status, func.count(Opportunity.id))
        .where(Opportunity.detected_at >= since)
        .group_by(Opportunity.status)).all()
    return [{"status": s, "count": c} for s, c in rows]


def portfolio_curve(session: Session, portfolio_id: str | None = None) -> list[dict]:
    q = select(Position).where(Position.status == "settled").order_by(Position.settled_at)
    if portfolio_id:
        q = q.where(Position.portfolio_id == portfolio_id)
    positions = session.execute(q).scalars().all()
    curve, cumulative = [], 0.0
    for p in positions:
        if p.settled_at is None:
            continue
        cumulative += p.profit or 0
        curve.append({"ts": p.settled_at.isoformat(), "profit": round(cumulative, 2),
                      "simulated": True})
    return curve


def odds_movements(session: Session, event_id: str, limit: int = 100) -> list[dict]:
    rows = session.execute(
        select(Odds).where(Odds.event_id == event_id,
                           Odds.previous_odds.is_not(None))
        .order_by(Odds.captured_at.desc()).limit(limit)).all()
    return [{
        "bookmaker": r.bookmaker_key, "market": r.market_key, "outcome": r.outcome,
        "from_odds": r.previous_odds, "to_odds": r.odds,
        "captured_at": r.captured_at.isoformat() if r.captured_at else None,
    } for r in rows]
