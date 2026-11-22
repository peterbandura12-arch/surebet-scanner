"""Market catalog and compatibility rules.

A market key fully identifies a bettable market *including any line*, e.g.
``h2h`` (3-way 1X2), ``ah_-1.5``, ``ou_2.5``. Two odds rows may only be
compared inside an arbitrage calculation when they share the exact same
market key *and* that key exists in the catalog for the event's sport.
"""
from dataclasses import dataclass

H = "home"
D = "draw"
A = "away"
O = "over"
U = "under"


@dataclass(frozen=True)
class MarketDef:
    key: str
    name: str
    sport: str
    category: str
    outcomes: tuple[str, ...]
    settlement_note: str = ""
    line: float | None = None


def _mk(key, name, sport, category, outcomes, settlement_note="", line=None):
    return MarketDef(key=key, name=name, sport=sport, category=category,
                     outcomes=tuple(outcomes), settlement_note=settlement_note, line=line)


H2H_FOOT = _mk("h2h", "Match Winner (1X2)", "football", "match_winner", [H, D, A],
               "Includes the draw; unsettled 3-way result market.")
H2H_BASKET = _mk("h2h", "Moneyline", "basketball", "match_winner", [H, A],
                 "No draw in basketball; overtime settled in match winner.")
H2H_TENNIS = _mk("h2h", "Match Winner", "tennis", "match_winner", [H, A],
                 "Full match winner, best-of-N sets.")
H2H_HOCKEY = _mk("h2h", "Match Winner (including draw)", "ice_hockey", "match_winner", [H, D, A],
                 "Regular-time 3-way result.")
H2H_BASEBALL = _mk("h2h", "Moneyline", "baseball", "match_winner", [H, A])
H2H_AMDFT = _mk("h2h", "Moneyline", "american_football", "match_winner", [H, A])
H2H_RUGBY = _mk("h2h", "Match Winner (including draw)", "rugby", "match_winner", [H, D, A])
_H2H_OTHER = [
    _mk("h2h", "Match Winner", s, "match_winner", [H, A])
    for s in ("volleyball", "handball", "cricket", "table_tennis", "esports")
]

_DC = [
    _mk("dc_1x", "Double Chance 1X", "football", "double_chance", [H, D],
        "Wins if home wins or draw."),
    _mk("dc_12", "Double Chance 12", "football", "double_chance", [H, A],
        "Wins if no draw."),
    _mk("dc_x2", "Double Chance X2", "football", "double_chance", [D, A],
        "Wins if away wins or draw."),
]
_DNB = [_mk("dnb", "Draw No Bet", "football", "draw_no_bet", [H, A],
            "Stake refunded on a draw.")]
_AH = [
    _mk(f"ah_{line:+.1f}", f"Asian Handicap {line:+.1f}", "football", "handicap",
        [H, A], f"Handicap {line:+.1f}; single line, stake returned on exact push.",
        line=line)
    for line in (-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0)
]
_OU_FOOT = [
    _mk(f"ou_{line:.1f}", f"Over/Under {line:.1f}", "football", "totals", [O, U],
        f"Total goals line {line:.1f}.", line=line)
    for line in (1.5, 2.5, 3.5)
]
_OU_BASKET = [
    _mk(f"ou_{line:.1f}", f"Over/Under {line:.1f}", "basketball", "totals", [O, U],
        line=line) for line in (205.5, 215.5, 225.5)
]
_SPREAD_BASKET = [
    _mk(f"sp_{line:+.1f}", f"Spread {line:+.1f}", "basketball", "handicap", [H, A],
        line=line) for line in (-6.5, -3.5, 3.5, 6.5)
]
_OU_TENNIS = [
    _mk(f"ou_games_{line:.1f}", f"Total Games {line:.1f}", "tennis", "totals", [O, U],
        line=line) for line in (21.5, 22.5)
]
_GH_TENNIS = [
    _mk(f"games_hcp_{line:+.1f}", f"Game Handicap {line:+.1f}", "tennis", "handicap",
        [H, A], line=line) for line in (-3.5, -1.5, 1.5, 3.5)
]
_OU_HOCKEY = [
    _mk(f"ou_{line:.1f}", f"Over/Under {line:.1f}", "ice_hockey", "totals", [O, U],
        line=line) for line in (4.5, 5.5)
]
_PL_HOCKEY = [
    _mk(f"ah_{line:+.1f}", f"Puck Line {line:+.1f}", "ice_hockey", "handicap", [H, A],
        line=line) for line in (-1.5, 1.5)
]
_OU_BASE = [_mk("ou_8.5", "Over/Under 8.5", "baseball", "totals", [O, U], line=8.5),
            _mk("ah_-1.5", "Run Line -1.5", "baseball", "handicap", [H, A], line=-1.5)]
_OU_AMDFT = [_mk("ou_44.5", "Over/Under 44.5", "american_football", "totals", [O, U], line=44.5),
             _mk("sp_-3.5", "Spread -3.5", "american_football", "handicap", [H, A], line=-3.5)]
_OU_RUGBY = [_mk("ou_45.5", "Over/Under 45.5", "rugby", "totals", [O, U], line=45.5)]
_OU_OTHER = {
    "volleyball": [_mk("ou_3.5", "Total Sets Over/Under 3.5", "volleyball", "totals", [O, U], line=3.5)],
    "handball": [_mk("ou_55.5", "Over/Under 55.5", "handball", "totals", [O, U], line=55.5)],
    "cricket": [_mk("ou_320.5", "Total Runs Over/Under 320.5", "cricket", "totals", [O, U], line=320.5)],
    "table_tennis": [_mk("ou_4.5", "Total Sets Over/Under 4.5", "table_tennis", "totals", [O, U], line=4.5)],
    "esports": [_mk("ou_2.5", "Total Maps Over/Under 2.5", "esports", "totals", [O, U], line=2.5)],
}

MARKETS: dict[tuple[str, str], MarketDef] = {}
for m in (H2H_FOOT, H2H_BASKET, H2H_TENNIS, H2H_HOCKEY, H2H_BASEBALL, H2H_AMDFT, H2H_RUGBY,
          *_H2H_OTHER, *_DC, *_DNB, *_AH, *_OU_FOOT, *_OU_BASKET, *_SPREAD_BASKET,
          *_OU_TENNIS, *_GH_TENNIS, *_OU_HOCKEY, *_PL_HOCKEY, *_OU_BASE, *_OU_AMDFT,
          *_OU_RUGBY, *_OU_OTHER.get("volleyball", []), *_OU_OTHER.get("handball", []),
          *_OU_OTHER.get("cricket", []), *_OU_OTHER.get("table_tennis", []),
          *_OU_OTHER.get("esports", [])):
    MARKETS[(m.sport, m.key)] = m

SPORTS: dict[str, dict] = {
    "football": {"name": "Football", "icon": "goal", "weight": 1.0},
    "basketball": {"name": "Basketball", "icon": "ball", "weight": 1.0},
    "tennis": {"name": "Tennis", "icon": "racket", "weight": 1.0},
    "ice_hockey": {"name": "Ice Hockey", "icon": "puck", "weight": 1.0},
    "baseball": {"name": "Baseball", "icon": "ball", "weight": 1.0},
    "volleyball": {"name": "Volleyball", "icon": "ball", "weight": 1.0},
    "american_football": {"name": "American Football", "icon": "ball", "weight": 1.0},
    "rugby": {"name": "Rugby", "icon": "ball", "weight": 1.0},
    "handball": {"name": "Handball", "icon": "ball", "weight": 1.0},
    "cricket": {"name": "Cricket", "icon": "bat", "weight": 1.0},
    "table_tennis": {"name": "Table Tennis", "icon": "racket", "weight": 1.0},
    "esports": {"name": "Esports", "icon": "monitor", "weight": 1.0},
}


def get_market(key: str, sport: str) -> MarketDef | None:
    """Resolve a market key *within the given sport*; keys are sport-scoped so
    'h2h' resolves to the 3-way 1X2 for football but the 2-way moneyline for
    basketball."""
    return MARKETS.get((sport, key))


def get_market_any_sport(key: str) -> list[MarketDef]:
    return [m for (s, k), m in MARKETS.items() if k == key]


def is_compatible(key_a: str, key_b: str, sport: str) -> bool:
    """Odds rows are only comparable when they resolve to the identical
    MarketDef (same category, same line, same settlement rules)."""
    if key_a != key_b:
        return False
    return get_market(key_a, sport) is not None


def markets_for_sport(sport: str) -> list[MarketDef]:
    return [m for m in MARKETS.values() if m.sport == sport]
