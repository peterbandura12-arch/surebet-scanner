"""Feed manager: pulls data from all configured providers, stores it and
matches provider events into canonical events.

Canonical events are established from the primary feed ("demo-a"); events
from other providers are matched against them with the multi-signal matching
engine in app/core/matching.py. Odds rows are append-only snapshots.
"""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import matching
from app.core.normalize import canonical_participant
from app.models import (Event, EventMatch, DataSource, Odds, Team, League,
                        utcnow)
from app.services.providers.demo import DemoOddsProvider
from app.services.providers.base import OddsProvider, ProviderEvent, PullResult

log = logging.getLogger(__name__)


def _team_id(session: Session, name: str, sport: str, league_id: str | None) -> Team:
    norm = canonical_participant(name)
    team = session.execute(
        select(Team).where(Team.normalized_name == norm, Team.sport_key == sport)
    ).scalar_one_or_none()
    if team is None:
        team = Team(name=name, normalized_name=norm, sport_key=sport,
                    league_id=league_id)
        session.add(team)
        session.flush()
    return team


def _league_id(session: Session, sport: str, league: str, country: str) -> League:
    import hashlib
    key = hashlib.sha1(league.lower().encode()).hexdigest()[:12]
    lg = session.execute(
        select(League).where(League.sport_key == sport, League.key == key)
    ).scalar_one_or_none()
    if lg is None:
        lg = League(sport_key=sport, key=key, name=league, country=country)
        session.add(lg)
        session.flush()
    return lg


def upsert_canonical_event(session: Session, provider_event: ProviderEvent) -> Event:
    """Create or return the canonical event for a primary-feed provider event."""
    league = _league_id(session, provider_event.sport, provider_event.league,
                        provider_event.league_country)
    home = _team_id(session, provider_event.home_name, provider_event.sport, league.id)
    away = _team_id(session, provider_event.away_name, provider_event.sport, league.id)
    name = f"{provider_event.home_name} vs {provider_event.away_name}"
    start_naive = provider_event.start_time.replace(tzinfo=None) \
        if provider_event.start_time.tzinfo else provider_event.start_time
    ev = session.execute(
        select(Event).where(Event.provider == provider_event.provider,
                            Event.external_id == provider_event.external_id)
    ).scalar_one_or_none()
    if ev is None:
        ev = Event(
            sport_key=provider_event.sport, league_id=league.id,
            home_team_id=home.id, away_team_id=away.id, name=name,
            start_time=start_naive, status=provider_event.status,
            provider=provider_event.provider,
            external_id=provider_event.external_id,
            match_group=f"g:{provider_event.external_id}")
        session.add(ev)
        session.flush()
    else:
        ev.start_time = start_naive
        ev.status = provider_event.status
    return ev


def match_provider_event(session: Session, provider_event: ProviderEvent,
                         confidence_log: list[dict] | None = None) -> Event | None:
    """Match a secondary-feed provider event to an existing canonical event."""
    existing = session.execute(
        select(EventMatch).where(EventMatch.provider == provider_event.provider,
                                 EventMatch.external_event_id == provider_event.external_id)
    ).scalar_one_or_none()
    if existing is not None:
        return session.get(Event, existing.event_id)

    start_naive = provider_event.start_time.replace(tzinfo=None) \
        if provider_event.start_time.tzinfo else provider_event.start_time
    candidates = session.execute(
        select(Event).where(
            Event.sport_key == provider_event.sport,
            Event.status.in_(("scheduled", "live")),
            Event.start_time >= start_naive - timedelta(hours=6),
            Event.start_time <= start_naive + timedelta(hours=6),
        )
    ).scalars().all()

    cand_events = [
        matching.EventCandidate(
            sport=e.sport_key,
            home_name=e.home_team.name if e.home_team else "",
            away_name=e.away_team.name if e.away_team else "",
            league=e.league.name if e.league else "",
            start_time=e.start_time.replace(tzinfo=None) if e.start_time else None,
            external_id=e.external_id, provider=e.provider)
        for e in candidates
    ]
    incoming = matching.EventCandidate(
        sport=provider_event.sport, home_name=provider_event.home_name,
        away_name=provider_event.away_name, league=provider_event.league,
        start_time=start_naive,
        external_id=provider_event.external_id, provider=provider_event.provider)
    cand_events = [c for c in cand_events if c.start_time and incoming.start_time]

    best_event, best_result = matching.find_best_match(incoming, cand_events)
    if best_event is None or best_result is None:
        if confidence_log is not None:
            confidence_log.append({
                "provider_event": f"{provider_event.home_name} vs {provider_event.away_name}",
                "matched": None, "confidence": 0.0})
        return None

    ev = session.execute(
        select(Event).where(Event.external_id == best_event.external_id,
                            Event.provider == best_event.provider)
    ).scalar_one_or_none()
    if ev is None:
        return None

    session.add(EventMatch(
        provider=provider_event.provider,
        external_event_id=provider_event.external_id,
        event_id=ev.id,
        confidence=best_result.confidence,
        method="auto",
        signals=best_result.signals))
    session.flush()
    if confidence_log is not None:
        confidence_log.append({
            "provider_event": f"{provider_event.home_name} vs {provider_event.away_name}",
            "matched": ev.name,
            "confidence": best_result.confidence,
            "needs_review": best_result.needs_review})
    return ev


def store_odds(session: Session, provider_event: ProviderEvent,
               event_id: str | None) -> int:
    """Append-only snapshot storage. Only changed values create new rows."""

    if event_id is None:
        return 0
    written = 0
    for po in provider_event.odds:
        last = session.execute(
            select(Odds).where(
                Odds.event_id == event_id,
                Odds.provider == provider_event.provider,
                Odds.external_event_id == po.external_event_id,
                Odds.bookmaker_key == po.bookmaker_key,
                Odds.market_key == po.market_key,
                Odds.outcome == po.outcome,
            ).order_by(Odds.captured_at.desc()).limit(1)
        ).scalar_one_or_none()
        if last is not None and abs(last.odds - po.odds) < 1e-9:
            continue
        session.add(Odds(
            event_id=event_id, provider=provider_event.provider,
            external_event_id=po.external_event_id,
            bookmaker_key=po.bookmaker_key, market_key=po.market_key,
            outcome=po.outcome, odds=po.odds,
            captured_at=po.captured_at,
            open_odds=last.odds if last is not None else po.odds,
            previous_odds=last.odds if last is not None else None))
        written += 1
    session.flush()
    return written


class FeedManager:
    def __init__(self, providers: list[OddsProvider] | None = None):
        from app.config import get_settings
        s = get_settings()
        self.providers = providers or [
            DemoOddsProvider(seed=s.demo_seed, feed_name="demo-a"),
            DemoOddsProvider(seed=s.demo_seed, feed_name="demo-b"),
        ]
        self._real_providers_cache: list[OddsProvider] = []
        self._real_provider_last_tick = 0.0

    def ensure_real_providers(self) -> list[OddsProvider]:
        """Append configured real providers (e.g. The Odds API) if not present."""
        if self._real_providers_cache:
            return self._real_providers_cache
        try:
            from app.services.providers.theoddsapi import TheOddsApiProvider
            self._real_providers_cache.append(TheOddsApiProvider())
            log.info("real provider enabled: theoddsapi (sports=%s)",
                     self._real_providers_cache[0].sports)
        except Exception as exc:
            log.debug("real provider not enabled: %s", exc)
        return self._real_providers_cache

    def tick(self, session: Session) -> dict:
        """Pull every provider, persist events/odds/matches. Returns a summary."""
        from app.config import get_settings
        s = get_settings()
        summary = {"providers": {}, "events": 0, "odds_rows": 0, "matches": [],
                   "warnings": []}
        all_providers = self.providers + self.ensure_real_providers()
        now = time.time()
        for provider in all_providers:
            if not provider.is_simulated:
                # Real API: protect the paid quota with a dedicated interval.
                if now - self._real_provider_last_tick < \
                        s.theoddsapi_min_interval_seconds:
                    summary["providers"][provider.key] = {
                        "skipped": "quota_interval"}
                    continue
            try:
                result: PullResult = provider.pull()
                if not provider.is_simulated:
                    self._real_provider_last_tick = time.time()
            except Exception as exc:  # provider outage must not kill the feed
                log.exception("provider %s failed", provider.key)
                summary["warnings"].append(f"{provider.key}: {exc}")
                self._record_source_status(session, provider.key,
                                           f"error: {exc}")
                continue
            summary["providers"][provider.key] = {"events": len(result.events),
                                                  "simulated": result.is_simulated}
            self._record_source_status(
                session, provider.key,
                "; ".join(result.warnings) if result.warnings else "")
            for pe in result.events:
                if pe.start_time is None:
                    continue
                primary = provider.key in ("demo-a", "demo") or not provider.is_simulated
                if primary:
                    ev = upsert_canonical_event(session, pe)
                    summary["events"] += 1
                else:
                    ev = match_provider_event(session, pe,
                                              confidence_log=summary["matches"])
                summary["odds_rows"] += store_odds(session, pe, ev.id if ev else None)
        summary["odds_rows"] = summary["odds_rows"]
        return summary

    @staticmethod
    def _record_source_status(session: Session, provider_key: str,
                              error: str) -> None:
        src = session.get(DataSource, provider_key)
        if src is None:
            return
        src.last_sync_at = utcnow()
        src.last_error = error or ""
