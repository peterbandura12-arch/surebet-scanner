"""Surebet scanner service.

Reads the latest odds snapshots for matched events, groups them strictly by
(event, market-key-with-line), resolves best odds per outcome across
bookmakers and uses the arbitrage engine in app/core/arbitrage.py to detect
opportunities. Persisted opportunities are tracked as active / expired with
snapshot history for ROI-over-time charts.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core import markets as mc
from app.core.arbitrage import sum_inverse
from app.models import Event, Odds, Opportunity, OpportunitySnapshot

log = logging.getLogger(__name__)


@dataclass
class ScanFinding:
    event: Event
    market_key: str
    market_name: str
    best: dict[str, dict]          # outcome -> {odds, bookmaker, captured_at, ...}
    sum_inv: float
    roi_pct: float
    is_arbitrage: bool
    notes: list[str] = field(default_factory=list)


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def load_latest_odds(session: Session, max_age: int | None = None,
                     event_ids: list[str] | None = None,
                     now: datetime | None = None) -> dict[tuple, dict]:
    """Return {(event_id, market_key, outcome): {odds, bookmaker, ...}}.

    Stage 1: freshest snapshot per (event, bookmaker, market, outcome).
    Stage 2: best (highest) odds per outcome across bookmakers.
    """
    s = get_settings()
    max_age = max_age if max_age is not None else s.odds_max_age_seconds
    now = now or datetime.now(timezone.utc)
    cutoff = _naive(now - timedelta(seconds=max_age))

    q = select(Odds).where(Odds.event_id.is_not(None),
                           Odds.captured_at >= cutoff,
                           Odds.odds > 1.0)
    if event_ids:
        q = q.where(Odds.event_id.in_(event_ids))
    q = q.options(joinedload(Odds.event))
    rows = session.execute(q).scalars().all()

    latest_per_book: dict[tuple, Odds] = {}
    for row in rows:
        key = (row.event_id, row.bookmaker_key, row.market_key, row.outcome)
        current = latest_per_book.get(key)
        if current is None or _naive(row.captured_at) >= _naive(current.captured_at):
            latest_per_book[key] = row

    best: dict[tuple, dict] = {}
    for (event_id, bookmaker, market_key, outcome), row in latest_per_book.items():
        captured = _naive(row.captured_at)
        age_seconds = (now.replace(tzinfo=None) - captured).total_seconds()
        info = {
            "odds": row.odds,
            "bookmaker": bookmaker,
            "captured_at": captured.replace(tzinfo=timezone.utc),
            "provider": row.provider,
            "external_event_id": row.external_event_id,
            "age_seconds": max(age_seconds, 0.0),
        }
        key = (event_id, market_key, outcome)
        current = best.get(key)
        if current is None or info["odds"] > current["odds"]:
            best[key] = info
    return best


def scan_events(session: Session, min_roi: float | None = None,
                event_ids: list[str] | None = None,
                max_age: int | None = None,
                bankroll: float = 1000.0) -> list[ScanFinding]:
    """Scan for arbitrage opportunities across the latest odds snapshots.

    Outcome compatibility is enforced by grouping on the exact market key
    (line included) and requiring the market definition of the event's sport
    to match the observed outcome set exactly. Incompatible settlement rules,
    lines or partial markets are never compared.
    """
    s = get_settings()
    min_roi = s.min_roi_pct if min_roi is None else min_roi
    latest = load_latest_odds(session, max_age=max_age, event_ids=event_ids)

    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for (event_id, market_key, outcome), info in latest.items():
        grouped[(event_id, market_key)][outcome] = info

    events = session.execute(
        select(Event).where(Event.status == "scheduled")
    ).scalars().all()
    event_map = {e.id: e for e in events}

    findings: list[ScanFinding] = []
    for (event_id, market_key), outcome_map in grouped.items():
        event = event_map.get(event_id)
        if event is None:
            continue
        mdef = mc.get_market(market_key, event.sport_key)
        if mdef is None:
            continue
        if set(outcome_map.keys()) != set(mdef.outcomes):
            continue

        ordered_outcomes = list(mdef.outcomes)
        odds_list = [outcome_map[o]["odds"] for o in ordered_outcomes]
        try:
            s_inv = sum_inverse(odds_list)
        except Exception:
            continue
        roi = (1.0 / s_inv - 1.0) * 100.0 if s_inv > 0 else 0.0

        notes: list[str] = []
        ages = [outcome_map[o]["age_seconds"] for o in ordered_outcomes]
        if max(ages) > s.odds_max_age_seconds * 0.75:
            notes.append("Some quotes are approaching freshness limits.")
        books = {outcome_map[o]["bookmaker"] for o in ordered_outcomes}
        if len(books) < len(ordered_outcomes):
            notes.append("All legs come from the same bookmaker.")

        findings.append(ScanFinding(
            event=event, market_key=market_key,
            market_name=mdef.name,
            best={o: outcome_map[o] for o in ordered_outcomes},
            sum_inv=s_inv, roi_pct=roi,
            is_arbitrage=(s_inv < 1.0 and roi >= min_roi),
            notes=notes))

    findings.sort(key=lambda f: f.roi_pct, reverse=True)
    return findings


def persist_scan(session: Session, min_roi: float | None = None,
                 bankroll: float = 1000.0) -> dict:
    """Run a scan and reconcile the opportunities table.

    Returns {"new": [...], "updated": [...], "expired": [...]}.
    """
    findings = scan_events(session, min_roi=min_roi, bankroll=bankroll)
    now = datetime.now(timezone.utc)
    result = {"new": [], "updated": [], "expired": [], "scanned_groups": len(findings)}

    active = session.execute(
        select(Opportunity).where(Opportunity.status == "active")
    ).scalars().all()
    active_keys = {(o.event_id, o.market_key): o for o in active}
    seen_keys: set[tuple[str, str]] = set()

    for f in findings:
        if not f.is_arbitrage:
            continue
        key = (f.event.id, f.market_key)
        seen_keys.add(key)
        mdef = mc.get_market(f.market_key, f.event.sport_key)
        legs = [
            {
                "outcome": o,
                "odds": f.best[o]["odds"],
                "bookmaker": f.best[o]["bookmaker"],
                "captured_at": f.best[o]["captured_at"].isoformat(),
                "age_seconds": round(f.best[o]["age_seconds"], 1),
            }
            for o in mdef.outcomes
        ]
        existing = active_keys.get(key)
        if existing is None:
            opp = Opportunity(
                event_id=f.event.id, market_key=f.market_key,
                market_name=f.market_name, sport_key=f.event.sport_key,
                league_name=f.event.league.name if f.event.league else "",
                event_name=f.event.name, start_time=f.event.start_time,
                roi_pct=f.roi_pct, sum_inverse=f.sum_inv,
                num_outcomes=len(legs), legs=legs, status="active",
                detected_at=now, last_seen_at=now, stale=bool(f.notes),
                validation_notes=f.notes)
            session.add(opp)
            session.flush()
            session.add(OpportunitySnapshot(opportunity_id=opp.id,
                                            roi_pct=f.roi_pct, legs=legs))
            result["new"].append(_serialize(opp))
        else:
            changed = abs(existing.roi_pct - f.roi_pct) > 1e-9
            existing.roi_pct = f.roi_pct
            existing.sum_inverse = f.sum_inv
            existing.legs = legs
            existing.last_seen_at = now
            existing.stale = bool(f.notes)
            existing.validation_notes = f.notes
            if changed:
                session.add(OpportunitySnapshot(opportunity_id=existing.id,
                                                roi_pct=f.roi_pct, legs=legs))
            result["updated"].append(_serialize(existing))

    for key, opp in active_keys.items():
        if key in seen_keys:
            continue
        opp.status = "expired"
        opp.expires_at = now
        result["expired"].append(_serialize(opp))

    session.flush()
    return result


def expire_stale_events(session: Session) -> int:
    """Mark events whose start time has passed as finished."""
    now = datetime.now(timezone.utc)
    live = session.execute(
        select(Event).where(Event.status == "scheduled",
                            Event.start_time < _naive(now))
    ).scalars().all()
    count = 0
    for ev in live:
        ev.status = "finished"
        count += 1
    if count:
        session.flush()
    return count


def _serialize(opp: Opportunity) -> dict:
    return {
        "id": opp.id,
        "event_id": opp.event_id,
        "event_name": opp.event_name,
        "league": opp.league_name,
        "sport": opp.sport_key,
        "market_key": opp.market_key,
        "market_name": opp.market_name,
        "start_time": opp.start_time.isoformat() if opp.start_time else None,
        "roi_pct": round(opp.roi_pct, 3),
        "sum_inverse": round(opp.sum_inverse, 5),
        "num_outcomes": opp.num_outcomes,
        "legs": opp.legs,
        "status": opp.status,
        "detected_at": opp.detected_at.isoformat() if opp.detected_at else None,
        "last_seen_at": opp.last_seen_at.isoformat() if opp.last_seen_at else None,
        "stale": opp.stale,
        "validation_notes": opp.validation_notes or [],
    }
