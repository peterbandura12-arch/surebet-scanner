from datetime import datetime, timedelta


from app.core import matching
from app.core.matching import (ACCEPT_THRESHOLD, EventCandidate,
                               are_equivalent, match_events,
                               participant_match_score)


def ev(home="Manchester City", away="Arsenal", sport="football",
       league="English Premier League", start=None, ext="x1"):
    return EventCandidate(sport, home, away, league,
                          start or datetime(2025, 3, 1, 20, 0), ext)


class TestParticipants:
    def test_identical(self):
        assert participant_match_score("Arsenal", "Arsenal") == 1.0

    def test_abbreviation(self):
        assert participant_match_score("Manchester City", "Man City") == 1.0
        assert participant_match_score("Manchester United", "Man Utd") == 1.0

    def test_unrelated(self):
        assert participant_match_score("Arsenal", "Bayern Munich") < 0.5

    def test_unrelated_names_are_not_confused(self):
        assert participant_match_score("Manchester City", "Manchester United") < 1.0


class TestEventMatching:
    def test_exact_match(self):
        r = match_events(ev(), ev())
        assert r.accepted and r.confidence >= ACCEPT_THRESHOLD

    def test_abbreviation_and_alias(self):
        b = ev(home="Man City", away="Arsenal FC", league="Premier League")
        r = match_events(ev(), b)
        assert r.accepted

    def test_reversed_home_away(self):
        b = ev(home="Arsenal", away="Manchester City", league="EPL")
        r = match_events(ev(), b)
        assert r.accepted
        assert r.signals["participants_reversed"]

    def test_time_proximity_required(self):
        far = ev(start=datetime(2025, 3, 1, 20, 0) + timedelta(hours=8))
        r = match_events(ev(), far)
        assert not r.accepted

    def test_same_time_same_league(self):
        near = ev(start=datetime(2025, 3, 1, 20, 4))
        assert match_events(ev(), near).accepted

    def test_sport_mismatch_never_matches(self):
        b = ev(sport="tennis")
        r = match_events(ev(), b)
        assert r.confidence == 0.0
        assert not r.accepted

    def test_unrelated_events_rejected(self):
        b = ev(home="Real Madrid", away="FC Barcelona",
               league="Spanish La Liga")
        r = match_events(ev(), b)
        assert not r.accepted
        assert not r.needs_review

    def test_confidence_in_range(self):
        for candidate in (ev(home="Man City"),
                          ev(home="FC Bayern Munich", league="Bundesliga"),
                          ev(league="La Liga")):
            r = match_events(ev(), candidate)
            assert 0.0 <= r.confidence <= 1.0


class TestAreEquivalent:
    def test_true_for_same(self):
        assert are_equivalent(ev(), ev())

    def test_false_far_apart(self):
        far = ev(start=datetime(2025, 3, 1, 20, 0) + timedelta(days=2))
        assert not are_equivalent(ev(), far)


class TestLeagueAliases:
    def test_alias_groups(self):
        assert matching.league_match_score("EPL", "English Premier League") == 1.0
        assert matching.league_match_score("La Liga", "LaLiga") == 1.0
        assert matching.league_match_score("Bundesliga", "Serie A") < 1.0


def test_find_best_match_picks_highest():
    a = ev()
    known = [ev(home="Manchester United", ext="x2"),
             ev(ext="x3"),
             ev(home="Real Madrid", away="Barcelona", ext="x4")]
    best, res = matching.find_best_match(a, known)
    assert best is not None and best.external_id == "x3"
    assert res.accepted
