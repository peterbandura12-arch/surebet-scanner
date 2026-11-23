"""Tests for real-provider integration pieces (no network, no credentials).

The Odds API provider is activated ONLY by its key; these tests exercise the
payload mapping and dynamic market registration with synthetic payloads.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core import markets as mc
from app.services.providers.theoddsapi import (TheOddsApiProvider, _map_sport,
                                               _parse_ts)


def _bare_provider() -> TheOddsApiProvider:
    """Provider instance bypassing __init__ (no key required for mapping tests)."""
    p = object.__new__(TheOddsApiProvider)
    p.api_key = ""
    p.sports = ["soccer_epl"]
    p.markets_param = "h2h,spreads,totals"
    p.region = "eu"
    p.requests_remaining = None
    p.requests_used = None
    p._last_request_ts = 0.0
    p._min_interval = 1.0
    return p


def _api_event() -> dict:
    return {
        "id": "ev123", "sport_key": "soccer_epl", "sport_title": "EPL",
        "home_team": "Arsenal", "away_team": "Chelsea",
        "commence_time": "2026-01-01T15:00:00Z",
        "bookmakers": [{
            "key": "pinnacle", "title": "Pinnacle",
            "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": "Arsenal", "price": 2.10},
                    {"name": "Draw", "price": 3.40},
                    {"name": "Chelsea", "price": 3.55}]},
                {"key": "spreads", "outcomes": [
                    {"name": "Arsenal", "price": 1.95, "point": -1.0},
                    {"name": "Chelsea", "price": 2.05, "point": 1.0}]},
                {"key": "totals", "outcomes": [
                    {"name": "Over", "price": 1.85, "point": 2.5},
                    {"name": "Under", "price": 2.00, "point": 2.5}]},
            ]}],
    }


class TestNotConfigured:
    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("THEODDSAPI_KEY", raising=False)
        from app.config import get_settings
        s = get_settings()
        original = s.theoddsapi_key
        s.theoddsapi_key = ""
        try:
            with pytest.raises(Exception):
                TheOddsApiProvider()
        finally:
            s.theoddsapi_key = original


class TestMapping:
    def test_h2h_three_way(self):
        p = _bare_provider()
        ev = p._convert(_api_event())
        assert ev.sport == "football"
        assert ev.league == "EPL"
        assert ev.start_time == datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)
        h2h = [o for o in ev.odds if o.market_key == "h2h"]
        assert {(o.outcome, o.odds) for o in h2h} == {
            ("home", 2.10), ("draw", 3.40), ("away", 3.55)}

    def test_bookmaker_prefix(self):
        p = _bare_provider()
        ev = p._convert(_api_event())
        assert {o.bookmaker_key for o in ev.odds} == {"toa_pinnacle"}

    def test_spread_pairs_single_line(self):
        p = _bare_provider()
        ev = p._convert(_api_event())
        spreads = [o for o in ev.odds if o.market_key.startswith("ah_")]
        assert {o.market_key for o in spreads} == {"ah_-1.0"}
        assert {(o.outcome, o.odds) for o in spreads} == {
            ("home", 1.95), ("away", 2.05)}
        mdef = mc.get_market("ah_-1.0", "football")
        assert mdef is not None and set(mdef.outcomes) == {"home", "away"}

    def test_totals_dynamic_line(self):
        p = _bare_provider()
        ev = p._convert(_api_event())
        totals = [o for o in ev.odds if o.market_key.startswith("ou_")]
        assert {o.market_key for o in totals} == {"ou_2.5"}
        assert {(o.outcome, o.odds) for o in totals} == {
            ("over", 1.85), ("under", 2.00)}

    def test_different_lines_are_incompatible(self):
        p = _bare_provider()
        ev1 = p._convert(_api_event())
        ev2 = p._convert(_api_event())
        for o in ev2.odds:
            if o.market_key == "ah_-1.0" and o.outcome == "away":
                o.market_key = "ah_+2.0"
        keys1 = {o.market_key for o in ev1.odds if o.market_key.startswith("ah_")}
        keys2 = {o.market_key for o in ev2.odds if o.market_key.startswith("ah_")}
        assert keys1 != keys2
        for k1 in keys1:
            for k2 in keys2:
                if k1 != k2:
                    mc.ensure_market("football", k1)
                    mc.ensure_market("football", k2)
                    assert not mc.is_compatible(k1, k2, "football")


class TestEnsureMarket:
    def test_unknown_dynamic_line_registered(self):
        mdef = mc.ensure_market("football", "ou_2.75")
        assert mdef is not None
        assert mdef.outcomes == ("over", "under")
        assert mdef.line == 2.75
        assert mc.get_market("ou_2.75", "football") is mdef

    def test_uninterpretable_key_rejected(self):
        assert mc.ensure_market("football", "weird/market") is None

    def test_lines_stay_incompatible(self):
        mc.ensure_market("football", "ou_3.25")
        assert not mc.is_compatible("ou_2.5", "ou_3.25", "football")

    def test_missing_defs_still_rejected(self):
        assert mc.ensure_market("football", "h2h_special") is None


class TestHelpers:
    def test_map_sport(self):
        assert _map_sport("soccer_epl") == "football"
        assert _map_sport("icehockey_nhl") == "ice_hockey"
        assert _map_sport("basketball_nba") == "basketball"
        assert _map_sport("whatever_new") == "other"

    def test_parse_ts(self):
        assert _parse_ts(None) is None
        assert _parse_ts("bad-ts") is None
        assert _parse_ts("2026-01-01T00:00:00Z") is not None
