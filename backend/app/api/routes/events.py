from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core import matching
from app.db import get_db
from app.models import (Event, EventMatch, Odds)
from app.services import analytics

router = APIRouter(tags=["events", "odds"])


@router.get("/events")
def list_events(
    sport: str | None = None,
    league: str | None = None,
    country: str | None = None,
    status: str | None = Query(None, pattern="^(scheduled|live|finished)$"),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = select(Event).options(joinedload(Event.league), joinedload(Event.home_team),
                              joinedload(Event.away_team))
    count_q = select(func.count(Event.id))
    if sport:
        q = q.where(Event.sport_key == sport)
        count_q = count_q.where(Event.sport_key == sport)
    if status:
        q = q.where(Event.status == status)
        count_q = count_q.where(Event.status == status)
    if search:
        q = q.where(Event.name.ilike(f"%{search}%"))
        count_q = count_q.where(Event.name.ilike(f"%{search}%"))
    total = db.execute(count_q).scalar() or 0
    events = db.execute(q.order_by(Event.start_time).offset(offset).limit(limit)).scalars().all()
    return {"total": total, "results": [_serialize_event(e) for e in events]}


@router.get("/events/{event_id}")
def event_detail(event_id: str, db: Session = Depends(get_db)):
    ev = db.get(Event, event_id)
    if ev is None:
        raise HTTPException(404, "event not found")
    odds = db.execute(
        select(Odds).where(Odds.event_id == event_id)
        .order_by(Odds.captured_at.desc()).limit(400)).scalars().all()
    latest: dict[tuple, Odds] = {}
    for row in odds:
        key = (row.bookmaker_key, row.market_key, row.outcome)
        if key not in latest:
            latest[key] = row
    comparison: dict[str, dict] = {}
    for (book, market, outcome), row in latest.items():
        m = comparison.setdefault(market, {"market_key": market,
                                           "bookmakers": {}})
        bm = m["bookmakers"].setdefault(book, {"bookmaker": book, "odds": {}})
        bm["odds"][outcome] = {"value": row.odds,
                               "captured_at": row.captured_at.isoformat() if row.captured_at else None}
    matches = db.execute(
        select(EventMatch).where(EventMatch.event_id == event_id)).scalars().all()
    data = _serialize_event(ev)
    data["markets"] = list(comparison.values())
    data["matches"] = [{
        "id": m.id, "provider": m.provider,
        "external_event_id": m.external_event_id, "confidence": m.confidence,
        "method": m.method, "manual": m.manual, "signals": m.signals,
    } for m in matches]
    return data


@router.get("/events/{event_id}/odds-movements")
def odds_movements(event_id: str, limit: int = Query(100, ge=1, le=500),
                   db: Session = Depends(get_db)):
    if db.get(Event, event_id) is None:
        raise HTTPException(404, "event not found")
    return {"simulated": True, "movements": analytics.odds_movements(db, event_id, limit)}


@router.get("/matching/review")
def matching_review(limit: int = Query(50, ge=1, le=200),
                    db: Session = Depends(get_db)):
    """Provider event matches in the manual-review confidence band."""
    matches = db.execute(
        select(EventMatch).where(EventMatch.confidence <
                                 matching.ACCEPT_THRESHOLD)
        .order_by(EventMatch.confidence.desc()).limit(limit)).scalars().all()
    return {"results": [{
        "match_id": m.id, "provider": m.provider,
        "external_event_id": m.external_event_id, "event_id": m.event_id,
        "confidence": m.confidence, "manual": m.manual, "signals": m.signals,
    } for m in matches]}


@router.patch("/matching/{match_id}")
def manual_match(match_id: str, body: dict, db: Session = Depends(get_db)):
    em = db.get(EventMatch, match_id)
    if em is None:
        raise HTTPException(404, "match not found")
    action = body.get("action")
    if action == "accept":
        em.manual = True
        em.confidence = 1.0
    elif action == "reject":
        em.confidence = 0.0
        em.manual = True
    elif action == "relink":
        new_event_id = body.get("event_id")
        if not new_event_id or db.get(Event, new_event_id) is None:
            raise HTTPException(400, "valid event_id required")
        em.event_id = new_event_id
        em.manual = True
        em.confidence = 1.0
    else:
        raise HTTPException(400, "action must be accept|reject|relink")
    db.commit()
    return {"id": em.id, "event_id": em.event_id, "manual": em.manual,
            "confidence": em.confidence}


def _serialize_event(e: Event) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "sport": e.sport_key,
        "league": e.league.name if e.league else "",
        "country": e.league.country if e.league else "",
        "home": e.home_team.name if e.home_team else "",
        "away": e.away_team.name if e.away_team else "",
        "start_time": e.start_time.isoformat() if e.start_time else None,
        "status": e.status,
        "provider": e.provider,
        "simulated": True,
    }
