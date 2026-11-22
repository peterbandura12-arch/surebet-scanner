"""DEMO data provider.

Generates a fully simulated but realistic odds universe: sports, leagues,
teams, fixtures, ~10 bookmakers with distinct margins, several markets per
event, live odds movement, stale/invalid/incomplete data, and occasional
genuine arbitrage opportunities. Everything this module produces is
SIMULATED and deterministic for a given seed (reproducible tests).

The scanner receives raw odds from this provider exactly like it would from
a real integration: arbitrage opportunities are *discovered* by scanning
combined odds, never handed out pre-computed by the generator.
"""
from __future__ import annotations

import math
import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha1

from app.core import markets as mc
from app.services.providers.base import (OddsProvider, ProviderEvent,
                                         ProviderOdds, PullResult)

BOOKMAKERS = [
    ("demoBet365", 1.045), ("demoWilliamHill", 1.055), ("demoBetfair", 1.020),
    ("demoUnibet", 1.050), ("demoBwin", 1.052), ("demoPinnacle", 1.015),
    ("demoMarathonbet", 1.022), ("demo1xBet", 1.035), ("demoKaramba", 1.060),
    ("demoNordicBet", 1.048), ("demoTipico", 1.058),
]

LEAGUES = {
    "football": [("epl", "English Premier League", "England"),
                 ("la_liga", "Spanish La Liga", "Spain"),
                 ("bundesliga", "German Bundesliga", "Germany"),
                 ("serie_a", "Italian Serie A", "Italy"),
                 ("ligue_1", "French Ligue 1", "France"),
                 ("ucl", "UEFA Champions League", "Europe")],
    "basketball": [("nba", "NBA", "USA"), ("euroleague", "EuroLeague", "Europe")],
    "tennis": [("atp_wimbledon", "ATP Wimbledon", "Great Britain"),
               ("atp_us_open", "ATP US Open", "USA")],
    "ice_hockey": [("nhl", "NHL", "USA"), ("khl", "KHL", "Russia")],
    " Baseball_placeholder": [],
}

TEAMS = {
    "epl": ["Arsenal", "Manchester City", "Liverpool", "Chelsea", "Tottenham Hotspur",
            "Manchester United", "Newcastle United", "Aston Villa", "West Ham United",
            "Everton"],
    "la_liga": ["Real Madrid", "FC Barcelona", "Atletico Madrid", "Sevilla",
                "Real Betis", "Athletic Bilbao", "Valencia", "Villarreal"],
    "bundesliga": ["Bayern Munich", "Borussia Dortmund", "RB Leipzig",
                   "Bayer Leverkusen", "VfB Stuttgart", "Eintracht Frankfurt"],
    "serie_a": ["Inter Milan", "AC Milan", "Juventus", "Napoli", "AS Roma",
                "Atalanta", "Lazio"],
    "ligue_1": ["Paris Saint-Germain", "Olympique Marseille", "AS Monaco",
                "Olympique Lyonnais", "Lille", "Nice"],
    "ucl": ["Bayern Munich", "Manchester City", "Real Madrid", "Inter Milan",
            "Paris Saint-Germain", "Arsenal", "FC Barcelona", "Borussia Dortmund"],
    "nba": ["Boston Celtics", "Denver Nuggets", "Milwaukee Bucks", "LA Lakers",
            "Golden State Warriors", "Phoenix Suns", "Miami Heat", "Dallas Mavericks"],
    "euroleague": ["Real Madrid", "FC Barcelona", "Panathinaikos", "Olympiacos",
                   "Fenerbahce", "Anadolu Efes"],
    "atp_wimbledon": [], "atp_us_open": [],
    "nhl": ["Boston Bruins", "Toronto Maple Leafs", "Colorado Avalanche",
            "Edmonton Oilers", "NY Rangers", "Vegas Golden Knights"],
    "khl": ["CSKA Moscow", "SKA Saint Petersburg", "Ak Bars Kazan", "Dynamo Moscow"],
}

TENNIS_PLAYERS = ["C. Alcaraz", "J. Sinner", "N. Djokovic", "D. Medvedev",
                  "A. Zverev", "A. Rublev", "H. Hurkacz", "S. Tsitsipas",
                  "T. Fritz", "F. Tiafoe", "C. Ruud", "A. de Minaur"]

# name variants used by the second feed ("demo-b") to exercise event matching
NAME_VARIANTS = {
    "Arsenal": ["Arsenal FC"],
    "Manchester City": ["Man City", "Manchester C"],
    "Manchester United": ["Man United", "Man Utd"],
    "Tottenham Hotspur": ["Tottenham", "Spurs"],
    "Newcastle United": ["Newcastle"],
    "West Ham United": ["West Ham"],
    "Real Madrid": ["Real Madrid CF"],
    "FC Barcelona": ["Barcelona", "Barca"],
    "Atletico Madrid": ["Atletico", "Atletico de Madrid"],
    "Bayern Munich": ["Bayern", "FC Bayern", "Bayern Munchen"],
    "Borussia Dortmund": ["Dortmund", "BVB"],
    "RB Leipzig": ["Leipzig"],
    "Bayer Leverkusen": ["Leverkusen", "Bayer 04"],
    "Internazionale": [],
    "Inter Milan": ["Inter", "Internazionale"],
    "AC Milan": ["Milan"],
    "Juventus": ["Juventus FC"],
    "Paris Saint-Germain": ["PSG", "Paris SG"],
    "Olympique Marseille": ["Marseille", "OM"],
    "Olympique Lyonnais": ["Lyon"],
    "LA Lakers": ["Los Angeles Lakers", "Lakers"],
    "Golden State Warriors": ["GS Warriors"],
    "NY Rangers": ["New York Rangers"],
    "Vegas Golden Knights": ["Vegas Knights"],
    "CSKA Moscow": ["CSKA"],
    "SKA Saint Petersburg": ["SKA"],
}

LEAGUE_VARIANTS = {
    "English Premier League": ["Premier League", "EPL", "England Premier League"],
    "Spanish La Liga": ["LaLiga", "La Liga", "Primera Division"],
    "German Bundesliga": ["Bundesliga", "Germany Bundesliga"],
    "Italian Serie A": ["Serie A", "Italy Serie A"],
    "French Ligue 1": ["Ligue 1", "France Ligue 1"],
    "NBA": ["National Basketball Association"],
    "NHL": ["National Hockey League"],
    "ATP Wimbledon": ["Wimbledon", "Wimbledon ATP"],
}

SPORT_MARKETS = {
    "football": ["h2h", "ou_2.5", "ah_-1.0", "dc_1x", "dnb"],
    "basketball": ["h2h", "ou_215.5", "sp_-3.5"],
    "tennis": ["h2h", "ou_games_22.5", "games_hcp_-1.5"],
    "ice_hockey": ["h2h", "ou_5.5", "ah_-1.5"],
    "baseball": ["h2h", "ou_8.5"],
    "volleyball": ["h2h", "ou_3.5"],
    "american_football": ["h2h", "ou_44.5"],
    "rugby": ["h2h"],
    "handball": ["h2h"],
    "cricket": ["h2h"],
    "table_tennis": ["h2h"],
    "esports": ["h2h"],
}

SECONDARY_SPORTS = [s for s in mc.SPORTS if s not in ("football", "basketball", "tennis", "ice_hockey")]
SECONDARY_TEAM_POOL = {
    "baseball": ["NY Yankees", "Boston Red Sox", "LA Dodgers", "Houston Astros"],
    "volleyball": ["Perugia", "Trentino", "Zenit Kazan", "Jastrzebski"],
    "american_football": ["KC Chiefs", "SF 49ers", "Buffalo Bills", "Dallas Cowboys"],
    "rugby": ["Leinster", "Toulouse", "Saracens", "La Rochelle"],
    "handball": ["Barca Handbol", "Kiel", "Magdeburg", "PSG Handball"],
    "cricket": ["India", "Australia", "England", "South Africa"],
    "table_tennis": ["Fan Zhendong", "Ma Long", "Wang Chuqin", "Harimoto"],
    "esports": ["NAVI", "FaZe Clan", "G2 Esports", "Team Vitality"],
}
SECONDARY_LEAGUE = {
    "baseball": "MLB", "volleyball": "Italian SuperLega", "american_football": "NFL",
    "rugby": "United Rugby Championship", "handball": "EHF Champions League",
    "cricket": "ICC World Cup", "table_tennis": "WTT Champions",
    "esports": "CS2 Majors",
}


def _rnd(seed: str) -> random.Random:
    return random.Random(int(sha1(seed.encode()).hexdigest(), 16) % (2**32))


_BASE_FIXTURE_CACHE: dict[int, list[dict]] = {}


def _base_fixtures(seed: int) -> list[dict]:
    """Canonical fixture list, deterministic per seed and independent of feed."""
    if seed in _BASE_FIXTURE_CACHE and _BASE_FIXTURE_CACHE[seed]:
        return _BASE_FIXTURE_CACHE[seed]
    rng = _rnd(f"fixtures-{seed}")
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    fixtures: list[dict] = []
    idx = 0

    league_map = {
        "football": LEAGUES.get("football", []),
        "basketball": LEAGUES.get("basketball", []),
        "ice_hockey": LEAGUES.get("ice_hockey", []),
    }
    for sport, leagues in league_map.items():
        for league_key, league_name, country in leagues:
            pool = list(TEAMS.get(league_key, []))
            rng.shuffle(pool)
            pairs_count = min(len(pool) // 2, 4 if sport == "football" else 2)
            for p in range(pairs_count):
                if len(pool) < 2 + p * 2:
                    break
                home, away = pool[p * 2], pool[p * 2 + 1]
                fixtures.append({
                    "sport": sport, "league_key": league_key,
                    "league": league_name, "country": country,
                    "home": home, "away": away,
                    "start": now + timedelta(hours=rng.uniform(1.5, 44.0)),
                    "id": f"dmA-{idx:04d}", "feed": "demo-a",
                })
                idx += 1

    for sport in SECONDARY_SPORTS:
        pool = SECONDARY_TEAM_POOL.get(sport, [])
        for p in range(2):
            home, away = pool[p * 2], pool[p * 2 + 1]
            fixtures.append({
                "sport": sport, "league_key": SECONDARY_LEAGUE[sport].lower(),
                "league": SECONDARY_LEAGUE[sport], "country": "International",
                "home": home, "away": away,
                "start": now + timedelta(hours=rng.uniform(2.0, 40.0)),
                "id": f"dmA-{idx:04d}", "feed": "demo-a",
            })
            idx += 1

    for i in range(8):
        p1 = TENNIS_PLAYERS[(i * 2) % len(TENNIS_PLAYERS)]
        p2 = TENNIS_PLAYERS[(i * 2 + 5) % len(TENNIS_PLAYERS)]
        league = "ATP Wimbledon" if i % 2 == 0 else "ATP US Open"
        fixtures.append({
            "sport": "tennis", "league_key": league.lower(), "league": league,
            "country": "International", "home": p1, "away": p2,
            "start": now + timedelta(hours=rng.uniform(1.0, 48.0)),
            "id": f"dmA-{idx:04d}", "feed": "demo-a",
        })
        idx += 1

    _BASE_FIXTURE_CACHE[seed] = fixtures
    return fixtures


class DemoOddsProvider(OddsProvider):
    key = "demo"
    name = "Demo Data Feed (simulated)"
    is_simulated = True

    def __init__(self, seed: int = 20240601, n_events: int = 60,
                 feed_name: str = "demo"):
        self.seed = seed
        self.n_events = n_events
        self.feed_name = feed_name
        self._fixtures: list[dict] | None = None
        self._state: dict[str, float] = {}
        self._bookmakers = BOOKMAKERS
        self.tick_count = 0
        self.variant_feed = feed_name == "demo-b"
        self.key = feed_name

    @property
    def fixtures(self) -> list[dict]:
        if self._fixtures is None:
            self._fixtures = self._build_fixtures()
        return self._fixtures

    def _build_fixtures(self) -> list[dict]:
        base = _base_fixtures(self.seed)
        if not self.variant_feed:
            return [dict(f) for f in base]
        out = []
        rng = _rnd(f"variants-{self.seed}")
        for f in base:
            home, away, league = f["home"], f["away"], f["league"]
            if NAME_VARIANTS.get(home) and rng.random() < 0.85:
                home = rng.choice(NAME_VARIANTS[home])
            if NAME_VARIANTS.get(away) and rng.random() < 0.85:
                away = rng.choice(NAME_VARIANTS[away])
            lv = LEAGUE_VARIANTS.get(league, [])
            if lv and rng.random() < 0.7:
                league = rng.choice(lv)
            out.append({**f, "home": home, "away": away, "league": league,
                        "start": f["start"] + timedelta(minutes=rng.uniform(-8, 8))})
        return out

    def _league_map(self) -> dict[str, list[tuple[str, str, str]]]:
        return {sport: [(k, n, c) for k, n, c in leagues]
                for sport, leagues in {
                    "football": LEAGUES.get("football", []),
                    "basketball": LEAGUES.get("basketball", []),
                    "ice_hockey": LEAGUES.get("ice_hockey", [])}.items()
                if leagues}

    def _true_probs(self, fixture: dict, market_key: str) -> dict[str, float]:
        mdef = mc.get_market(market_key, fixture["sport"])
        assert mdef
        base_id = fixture["id"].replace("dmA-", "")
        rng = _rnd(f"{base_id}-{market_key}-{self.seed}")
        raw = [rng.uniform(0.6, 1.0) for _ in mdef.outcomes]
        total = sum(raw)
        probs = {o: r / total for o, r in zip(mdef.outcomes, raw)}
        if mdef.category == "match_winner" and "home" in probs:
            home_p = probs["home"]
            probs["home"] = max(0.05, min(0.85, home_p))
            rest = 1.0 - probs["home"]
            others = [o for o in probs if o != "home"]
            osum = sum(probs[o] for o in others) or 1.0
            for o in others:
                probs[o] = probs[o] / osum * rest
        total = sum(probs.values())
        return {o: p / total for o, p in probs.items()}

    def _initial_odds(self, fixture: dict) -> list[ProviderOdds]:
        out: list[ProviderOdds] = []
        now = datetime.now(timezone.utc)
        sport_markets = SPORT_MARKETS.get(fixture["sport"], ["h2h"])
        for bm_key, margin in self._bookmakers:
            for market_key in sport_markets:
                probs = self._true_probs(fixture, market_key)
                rng = _rnd(f"init-{self.key}-{fixture['id']}-{market_key}-{bm_key}-{self.seed}")
                drop = rng.random()
                if drop < 0.10:
                    continue
                incomplete = rng.random() < 0.04
                quotes: list[ProviderOdds] = []
                for outcome in probs:
                    if incomplete and rng.random() < 0.4:
                        continue
                    noise = math.exp(rng.gauss(0.0, 0.012))
                    odds = round(1.0 / probs[outcome] / margin * noise, 2)
                    stale = rng.random() < 0.02
                    captured = now - timedelta(seconds=rng.uniform(600, 1200)) if stale \
                        else now - timedelta(seconds=rng.uniform(1, 90))
                    bad = rng.random() < 0.005
                    value = odds if not bad else round(rng.uniform(0.5, 0.99), 2)
                    quotes.append(ProviderOdds(
                        external_event_id=fixture["id"], bookmaker_key=bm_key,
                        market_key=market_key, outcome=outcome, odds=value,
                        captured_at=captured, is_stale=stale or bad))
                if quotes and rng.random() < 0.20:
                    # "slow book" simulation: one bookmaker lags the market on a
                    # single outcome, which is how real arbitrage appears
                    slow_book = quotes[0]
                    boost = math.exp(rng.uniform(0.04, 0.12))
                    new_val = round(slow_book.odds * boost, 2)
                    quotes[0] = replace(slow_book, odds=new_val)
                out.extend(quotes)
        return out

    def pull(self) -> PullResult:
        """Produce current provider events + odds.

        First call builds fixtures and initial odds. Subsequent calls run one
        simulated market move (random walk) each tick, occasionally creating
        or destroying arbitrage situations.
        """
        if self.tick_count == 0:
            self._initial_snapshot()
        else:
            self._simulate_movement()
        self.tick_count += 1
        rng = _rnd(f"tickmeta-{self.key}-{self.tick_count}-{self.seed}")
        # independent extra drift between the two feeds
        if self.variant_feed:
            for key in list(self._state.keys()):
                if rng.random() < 0.15:
                    new = round(self._state[key] * math.exp(rng.gauss(0, 0.01)), 2)
                    if new >= 1.01:
                        self._state[key] = new

        events: list[ProviderEvent] = []
        for fixture in self.fixtures:
            pe = ProviderEvent(
                provider=self.key, external_id=fixture["id"], sport=fixture["sport"],
                league=fixture["league"], league_country=fixture["country"],
                home_name=fixture["home"], away_name=fixture["away"],
                start_time=fixture["start"], status="scheduled")
            pe.odds = [o for o in self._odds_for(fixture["id"])
                       if o.external_event_id == fixture["id"]]
            events.append(pe)
        return PullResult(events=events, is_simulated=True)

    def _initial_snapshot(self) -> None:
        for fixture in self.fixtures:
            for o in self._initial_odds(fixture):
                self._state[f"{fixture['id']}|{o.bookmaker_key}|{o.market_key}|{o.outcome}"] = o.odds

    def _odds_for(self, event_id: str) -> list[ProviderOdds]:
        now = datetime.now(timezone.utc)
        next(f for f in self.fixtures if f["id"] == event_id)
        rng = _rnd(f"meta-{event_id}-{self.seed}")
        out = []
        for key, value in self._state.items():
            if not key.startswith(event_id + "|"):
                continue
            _, bm_k, m_k, outcome = key.split("|", 3)
            stale = rng.random() < 0.015
            out.append(ProviderOdds(
                external_event_id=event_id, bookmaker_key=bm_k, market_key=m_k,
                outcome=outcome, odds=value,
                captured_at=now - timedelta(seconds=rng.uniform(400, 1000)) if stale
                else now,
                is_stale=stale))
        return out

    def _simulate_movement(self) -> None:
        rng = _rnd(f"tick-{self.key}-{self.tick_count}-{self.seed}")
        keys = list(self._state.keys())
        n = max(1, int(len(keys) * 0.25))
        for key in rng.sample(keys, n):
            drift = rng.choice((-1, 1)) * rng.uniform(0.002, 0.02)
            if rng.random() < 0.02:
                drift *= rng.uniform(3, 6)
            new = round(self._state[key] * math.exp(drift), 2)
            if new >= 1.01:
                self._state[key] = new
