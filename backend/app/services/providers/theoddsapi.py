"""The Odds API provider (optional, real integration).

Activated only when THEODDSAPI_KEY is present in the environment. Uses the
documented v4 endpoints with polite rate limiting. When the provider fails,
empty data + a warning is returned: real outages are never masked by fake
data.

Market mapping (The Odds API -> internal):
- h2h     -> "h2h" (3-way when a draw price exists, else 2-way)
- spreads -> "ah_{line}" where line = home handicap; only paired
            (point, -point) outcomes are accepted
- totals  -> "ou_{line}" with over/under

Every line-bearing key is registered via markets.ensure_market so the scanner
can group it, while two different lines can never be compared with each other.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.core import markets as mc
from app.services.providers.base import (OddsProvider, ProviderEvent,
                                         ProviderNotConfigured, ProviderOdds,
                                         PullResult)

log = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"


def _fmt_line(value: float) -> str:
    if value == int(value):
        return f"{int(value):+d}.0"
    return f"{value:g}"


class TheOddsApiProvider(OddsProvider):
    key = "theoddsapi"
    name = "The Odds API (the-odds-api.com)"
    is_simulated = False
    requires_api_key = True
    docs_url = "https://the-odds-api.com/liveapi/guides/v4/"

    def __init__(self, sport_key: str | None = None):
        s = get_settings()
        self.api_key = s.theoddsapi_key or os.environ.get("THEODDSAPI_KEY", "")
        if not self.api_key:
            raise ProviderNotConfigured("THEODDSAPI_KEY is not set")
        self.sports = [x.strip() for x in
                       (sport_key or s.theoddsapi_sports).split(",") if x.strip()]
        if not self.sports:
            self.sports = [s.theoddsapi_sport]
        self.markets_param = s.theoddsapi_markets
        self.region = s.theoddsapi_region
        self._last_request_ts = 0.0
        self._min_interval = 1.0
        self.requests_remaining: int | None = None
        self.requests_used: int | None = None

    def _throttle(self) -> None:
        wait = self._min_interval - (time.time() - self._last_request_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_request_ts = time.time()

    def pull(self) -> PullResult:
        events: list[ProviderEvent] = []
        warnings: list[str] = []
        for sport in self.sports:
            evts, warn = self._pull_sport(sport)
            events.extend(evts)
            warnings.extend(warn)
        return PullResult(events=events, is_simulated=False, warnings=warnings)

    def _pull_sport(self, sport: str) -> tuple[list[ProviderEvent], list[str]]:
        self._throttle()
        url = f"{BASE_URL}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": self.region,
            "markets": self.markets_param,
            "oddsFormat": "decimal",
        }
        try:
            resp = httpx.get(url, params=params, timeout=15.0)
        except httpx.HTTPError as exc:
            log.warning("the-odds-api request failed: %s", exc)
            return [], [f"network_error: {exc}"]
        self.requests_remaining = resp.headers.get("x-requests-remaining")
        self.requests_used = resp.headers.get("x-requests-used")
        if resp.status_code == 429:
            return [], ["rate_limited: 429 from the-odds-api"]
        if resp.status_code == 401:
            return [], ["invalid_api_key: 401 from the-odds-api"]
        if resp.status_code == 404:
            return [], [f"unknown_sport: {sport} (404)"]
        if resp.status_code != 200:
            return [], [f"http_error: {resp.status_code}"]

        try:
            payload = resp.json()
        except ValueError:
            return [], ["invalid_payload: response is not JSON"]
        return [self._convert(item) for item in payload if item.get("id")], []

    def _convert(self, item: dict) -> ProviderEvent:
        sport = _map_sport(item.get("sport_key", ""))
        ev = ProviderEvent(
            provider=self.key, external_id=item.get("id", ""),
            sport=sport,
            league=item.get("sport_title", ""),
            home_name=item.get("home_team", ""),
            away_name=item.get("away_team", ""),
            start_time=_parse_ts(item.get("commence_time")))
        for bm in item.get("bookmakers", []):
            bk = f"toa_{bm.get('key', 'unknown')}"
            for mkt in bm.get("markets", []):
                self._convert_market(ev, bk, mkt)
        return ev

    def _convert_market(self, ev: ProviderEvent, bookmaker: str, mkt: dict) -> None:
        mkey = mkt.get("key")
        outcomes = mkt.get("outcomes", [])
        if mkey == "h2h":
            for oc in outcomes:
                price = oc.get("price")
                outcome = self._outcome_of(ev, oc.get("name", ""))
                if not price or price <= 1.0 or outcome is None:
                    continue
                ev.odds.append(ProviderOdds(
                    external_event_id=ev.external_id, bookmaker_key=bookmaker,
                    market_key="h2h", outcome=outcome, odds=float(price),
                    captured_at=datetime.now(timezone.utc)))
        elif mkey == "spreads":
            line = self._spread_line(ev, outcomes)
            if line is None:
                return
            mc.ensure_market(ev.sport, f"ah_{_fmt_line(line)}")
            for oc in outcomes:
                point = oc.get("point")
                price = oc.get("price")
                outcome = self._outcome_of(ev, oc.get("name", ""))
                if price is None or price <= 1.0 or outcome is None:
                    continue
                if outcome == "home" and point is not None and float(point) != line:
                    continue
                if outcome == "away" and point is not None and float(point) != -line:
                    continue
                ev.odds.append(ProviderOdds(
                    external_event_id=ev.external_id, bookmaker_key=bookmaker,
                    market_key=f"ah_{_fmt_line(line)}", outcome=outcome,
                    odds=float(price), captured_at=datetime.now(timezone.utc)))
        elif mkey == "totals":
            line = next((oc.get("point") for oc in outcomes
                         if oc.get("point") is not None), None)
            if line is None:
                return
            key = f"ou_{float(line):g}"
            mc.ensure_market(ev.sport, key, "totals")
            for oc in outcomes:
                name = oc.get("name", "").lower()
                outcome = "over" if name == "over" else (
                    "under" if name == "under" else None)
                price = oc.get("price")
                if price is None or price <= 1.0 or outcome is None:
                    continue
                if oc.get("point") is not None and float(oc["point"]) != float(line):
                    continue
                ev.odds.append(ProviderOdds(
                    external_event_id=ev.external_id, bookmaker_key=bookmaker,
                    market_key=key, outcome=outcome, odds=float(price),
                    captured_at=datetime.now(timezone.utc)))

    @staticmethod
    def _outcome_of(ev: ProviderEvent, name: str) -> str | None:
        if name == ev.home_name:
            return "home"
        if name == ev.away_name:
            return "away"
        if name.lower() == "draw":
            return "draw"
        return None

    @staticmethod
    def _spread_line(ev: ProviderEvent, outcomes: list[dict]) -> float | None:
        """Resolve the home-side handicap line from a paired spread market."""
        for oc in outcomes:
            if oc.get("name") == ev.home_name and oc.get("point") is not None:
                return float(oc["point"])
        for oc in outcomes:
            if oc.get("name") == ev.away_name and oc.get("point") is not None:
                return -float(oc["point"])
        return None


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _map_sport(sport_key: str) -> str:
    mapping = {
        "soccer": "football", "basketball": "basketball", "tennis": "tennis",
        "icehockey": "ice_hockey", "baseball": "baseball",
        "americanfootball": "american_football", "rugby": "rugby",
        "mma": "other",
    }
    prefix = sport_key.split("_", 1)[0]
    return mapping.get(prefix, "other")
