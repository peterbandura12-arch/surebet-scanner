"""The Odds API provider (optional, real integration).

Activated only when THEODDSAPI_KEY is present in the environment. Uses the
documented v4 endpoints with polite rate limiting. When the provider fails,
empty data + a warning is returned: real outages are never masked by fake
data.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.services.providers.base import (OddsProvider, ProviderEvent,
                                         ProviderNotConfigured, ProviderOdds,
                                         PullResult)

log = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"


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
        self.sport_key = sport_key or s.theoddsapi_sport
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
        self._throttle()
        url = f"{BASE_URL}/sports/{self.sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": self.region,
            "markets": "h2h",
            "oddsFormat": "decimal",
        }
        warnings: list[str] = []
        try:
            resp = httpx.get(url, params=params, timeout=15.0)
        except httpx.HTTPError as exc:
            log.warning("the-odds-api request failed: %s", exc)
            return PullResult(events=[], is_simulated=False,
                              warnings=[f"network_error: {exc}"])
        self.requests_remaining = resp.headers.get("x-requests-remaining")
        self.requests_used = resp.headers.get("x-requests-used")
        if resp.status_code == 429:
            return PullResult(events=[], is_simulated=False,
                              warnings=["rate_limited: 429 from the-odds-api"])
        if resp.status_code != 200:
            return PullResult(events=[], is_simulated=False,
                              warnings=[f"http_error: {resp.status_code}"])

        events: list[ProviderEvent] = []
        for item in resp.json():
            bookmakers = item.get("bookmakers", [])
            start = _parse_ts(item.get("commence_time"))
            ev = ProviderEvent(
                provider=self.key, external_id=item.get("id", ""),
                sport=_map_sport(item.get("sport_key", "")),
                league=item.get("sport_title", ""),
                home_name=item.get("home_team", ""),
                away_name=item.get("away_team", ""),
                start_time=start)
            for bm in bookmakers:
                bk = f"toa_{bm.get('key', 'unknown')}"
                for mkt in bm.get("markets", []):
                    if mkt.get("key") != "h2h":
                        continue
                    for oc in mkt.get("outcomes", []):
                        name = oc.get("name", "")
                        outcome = ("home" if name == ev.home_name
                                   else "away" if name == ev.away_name
                                   else "draw")
                        price = oc.get("price")
                        if not price or price <= 1.0:
                            continue
                        ev.odds.append(ProviderOdds(
                            external_event_id=ev.external_id,
                            bookmaker_key=bk, market_key="h2h",
                            outcome=outcome, odds=float(price),
                            captured_at=datetime.now(timezone.utc)))
            events.append(ev)
        return PullResult(events=events, is_simulated=False, warnings=warnings)


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
