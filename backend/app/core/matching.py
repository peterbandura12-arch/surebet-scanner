"""Event matching engine.

Determines whether two provider event descriptions refer to the same real
sporting event. Matching is deliberately multi-signal, never fuzzy-text-only:

1. sport must be identical (hard requirement)
2. participant similarity (order-insensitive), combining:
   - canonical/abbreviation equality (e.g. "Man City" == "Manchester City")
   - token Jaccard similarity on normalised names
   - prefix-aware similarity ("Benfica" vs "SL Benfica")
3. league alias similarity
4. kickoff time proximity

The result is a confidence score in [0, 1]. Scores above ``ACCEPT`` become
automatic matches; scores in the ``REVIEW`` band are flagged for manual
correction; below that they are rejected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.normalize import canonical_participant, normalize_team_name, strip_accents

ACCEPT_THRESHOLD = 0.82
REVIEW_THRESHOLD = 0.55

_LEAGUE_ALIASES = {
    "english premier league": ["premier league", "epl", "england premier league",
                               "premier league england"],
    "spanish la liga": ["la liga", "laliga", "primera division", "la liga spain"],
    "german bundesliga": ["bundesliga", "germany bundesliga"],
    "italian serie a": ["serie a", "italy serie a"],
    "french ligue 1": ["ligue 1", "france ligue 1"],
    "uefa champions league": ["champions league", "ucl", "uefa cl"],
    "nba": ["national basketball association", "usa nba"],
    "atp wimbledon": ["wimbledon", "wimbledon men", "wimbledon atp"],
    "nhl": ["national hockey league", "usa nhl"],
}


@dataclass(frozen=True)
class EventCandidate:
    """A provider-facing event description to be matched."""
    sport: str
    home_name: str
    away_name: str
    league: str
    start_time: datetime
    external_id: str = ""
    provider: str = ""


@dataclass
class MatchResult:
    confidence: float
    accepted: bool
    needs_review: bool
    signals: dict = field(default_factory=dict)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _prefix_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 3 and long_.startswith(short):
        return 0.85
    return 0.0


def participant_match_score(name_a: str, name_b: str) -> float:
    """Similarity between two participant names in [0, 1]."""
    na, nb = canonical_participant(name_a), canonical_participant(name_b)
    if na == nb:
        return 1.0
    ta, tb = normalize_team_name(name_a), normalize_team_name(name_b)
    scores = [_jaccard(set(ta.split()), set(tb.split())),
              _prefix_score(ta, tb)]
    return max(scores)


def league_match_score(league_a: str, league_b: str) -> float:
    la = strip_accents(league_a or "").lower().strip()
    lb = strip_accents(league_b or "").lower().strip()
    if not la or not lb:
        return 0.5
    if la == lb:
        return 1.0
    for canonical, aliases in _LEAGUE_ALIASES.items():
        group = {canonical, *aliases}
        if la in group and lb in group:
            return 1.0
    return _jaccard(set(la.split()), set(lb.split()))


def time_match_score(t_a: datetime, t_b: datetime) -> float:
    """1.0 for identical kickoff, decaying with distance (minutes)."""
    delta = abs((t_a - t_b).total_seconds()) / 60.0
    if delta <= 5:
        return 1.0
    if delta <= 15:
        return 0.9
    if delta <= 30:
        return 0.75
    if delta <= 60:
        return 0.4
    if delta <= 180:
        return 0.1
    return 0.0


def match_events(a: EventCandidate, b: EventCandidate) -> MatchResult:
    if a.sport != b.sport:
        return MatchResult(0.0, False, False, {"reason": "sport_mismatch"})

    ph = participant_match_score(a.home_name, b.home_name)
    pa = participant_match_score(a.away_name, b.away_name)
    direct = (ph + pa) / 2

    phx = participant_match_score(a.home_name, b.away_name)
    pax = participant_match_score(a.away_name, b.home_name)
    cross = (phx + pax) / 2

    # providers sometimes list fixtures with swapped home/away; treat a strong
    # cross match as the same event with a small penalty instead of ignoring it
    if cross > direct:
        p_score = cross * 0.93
        reversed_home_away = True
    else:
        p_score = direct
        reversed_home_away = False

    l_score = league_match_score(a.league, b.league)
    t_score = time_match_score(a.start_time, b.start_time)

    confidence = 0.55 * p_score + 0.15 * l_score + 0.30 * t_score
    conf_boost = 0.0
    if direct == 1.0 and t_score >= 0.75:
        conf_boost = 0.08
    confidence = min(1.0, confidence + conf_boost)

    accepted = confidence >= ACCEPT_THRESHOLD
    needs_review = (not accepted) and confidence >= REVIEW_THRESHOLD
    return MatchResult(
        confidence=round(confidence, 4),
        accepted=accepted,
        needs_review=needs_review,
        signals={
            "participant_home": round(ph, 4),
            "participant_away": round(pa, 4),
            "cross_axis": round(cross, 4),
            "participants_reversed": reversed_home_away,
            "league": round(l_score, 4),
            "time": round(t_score, 4),
        },
    )


def find_best_match(candidate: EventCandidate,
                    known: list[EventCandidate]) -> tuple[EventCandidate | None, MatchResult | None]:
    best: tuple[EventCandidate | None, MatchResult | None] = (None, None)
    for k in known:
        res = match_events(candidate, k)
        if best[1] is None or res.confidence > best[1].confidence:
            best = (k, res)
    if best[1] is not None and not best[1].accepted:
        return (None, best[1]) if not best[1].needs_review else best
    return best


def are_equivalent(a: EventCandidate, b: EventCandidate,
                   max_hours_apart: float = 6.0) -> bool:
    if abs((a.start_time - b.start_time)) > timedelta(hours=max_hours_apart):
        return False
    return match_events(a, b).accepted
