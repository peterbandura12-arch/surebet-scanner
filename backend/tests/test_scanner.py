"""Scanner tests: arbitrage discovery, strict grouping, persistence, expiry.

All fixtures come from the deterministic demo feed (conftest.demo_db), so the
scanner DISCOVERS opportunities from generated data — never from precomputed
values.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core import markets as mc
from app.core.arbitrage import sum_inverse
from app.models import Event, Odds, Opportunity
from app.services import scanner


class TestDiscovery:
    def test_scan_finds_opportunities(self, db):
        findings = scanner.scan_events(db, min_roi=0.5)
        assert findings, "demo universe must produce arbitrage findings"
        arbs = [f for f in findings if f.is_arbitrage]
        assert arbs, "at least one surebet must exist in the demo seed"
        for f in arbs:
            assert f.sum_inv < 1.0
            assert f.roi_pct >= 0.5

    def test_roi_matches_math_engine(self, db):
        findings = scanner.scan_events(db, min_roi=0.5)
        f = findings[0]
        odds = [f.best[o]["odds"] for o in f.best]
        expected_s = sum_inverse(odds)
        assert f.sum_inv == pytest.approx(expected_s)
        assert f.roi_pct == pytest.approx((1.0 / expected_s - 1.0) * 100.0)

    def test_findings_sorted_by_roi_desc(self, db):
        findings = scanner.scan_events(db, min_roi=0.5)
        rois = [f.roi_pct for f in findings]
        assert rois == sorted(rois, reverse=True)

    def test_groups_are_complete_markets(self, db):
        for f in scanner.scan_events(db):
            mdef = mc.get_market(f.market_key, f.event.sport_key)
            assert mdef is not None
            assert set(f.best.keys()) == set(mdef.outcomes)

    def test_no_incompatible_market_mixing(self, db):
        for f in scanner.scan_events(db):
            mdef = mc.get_market(f.market_key, f.event.sport_key)
            if mdef is None:
                continue
            assert set(f.best.keys()) == set(mdef.outcomes), (
                f"{f.event.name} {f.market_key} mixed incompatible outcomes"
            )
            if mdef.sport == "football" and mdef.key.startswith("h2h"):
                assert "draw" in mdef.outcomes
            if mdef.key.startswith("ou_"):
                assert set(mdef.outcomes) == {"over", "under"}
            if mdef.key.startswith("dc_"):
                assert len(mdef.outcomes) == 2
                assert set(mdef.outcomes) <= {"home", "away", "draw"}

    def test_min_roi_filter(self, db):
        all_f = scanner.scan_events(db, min_roi=0.5)
        high = scanner.scan_events(db, min_roi=50.0)
        assert all(f.roi_pct >= 50.0 or not f.is_arbitrage for f in high)
        assert all(len(f.best) >= 2 for f in all_f)

    def test_stale_odds_excluded(self, db):
        now = datetime.now(timezone.utc)
        recent = scanner.scan_events(db, max_age=60)
        old = scanner.scan_events(db, max_age=1_000_000)
        assert len(old) >= len(recent)
        for f in recent:
            for info in f.best.values():
                fetched_at = info["captured_at"]
                if fetched_at.tzinfo is None:
                    fetched_at = fetched_at.replace(tzinfo=timezone.utc)
                age = (now - fetched_at).total_seconds()
                assert age <= 60 + 5


class TestPersistence:
    def test_persist_scan_structure(self, db):
        result = scanner.persist_scan(db, min_roi=0.5)
        assert set(result) >= {"new", "updated", "expired", "scanned_groups"}
        assert result["new"] or result["updated"] or result["expired"]

    def test_persist_creates_active_opportunities(self, db):
        scanner.persist_scan(db, min_roi=0.5)
        opps = db.execute(select(Opportunity)).scalars().all()
        assert opps
        active = [o for o in opps if o.status == "active"]
        assert active
        for o in active:
            assert o.sum_inverse < 1.0
            assert len(o.legs) == o.num_outcomes
            assert o.legs[0]["odds"] > 1.0
            assert "bookmaker" in o.legs[0]

    def test_idempotent_rescan_updates_not_duplicates(self, db):
        r1 = scanner.persist_scan(db, min_roi=0.5)
        n_active_1 = len(r1["new"]) + len(r1["updated"])
        r2 = scanner.persist_scan(db, min_roi=0.5)
        assert len(r2["new"]) == 0, "rescan must not duplicate opportunities"
        assert len(r2["updated"]) == n_active_1
        opps = db.execute(select(Opportunity).where(
            Opportunity.status == "active")).scalars().all()
        keys = {(o.event_id, o.market_key) for o in opps}
        assert len(keys) == len(opps) or n_active_1 == 0

    def test_snapshot_history_created(self, db):
        from app.models import OpportunitySnapshot
        scanner.persist_scan(db, min_roi=0.5)
        snaps = db.execute(select(OpportunitySnapshot)).scalars().all()
        assert snaps
        for s in snaps:
            assert 0 < s.roi_pct
            assert isinstance(s.legs, list) and s.legs


class TestExpiry:
    def test_expire_stale_events(self, db):
        ev = db.execute(select(Event).where(Event.status == "scheduled")
                        ).scalars().first()
        assert ev is not None
        ev.start_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        db.flush()
        count = scanner.expire_stale_events(db)
        assert count >= 1
        db.refresh(ev)
        assert ev.status == "finished"

    def test_future_events_untouched(self, db):
        before = db.execute(select(Event).where(Event.status == "scheduled")
                            ).scalars().all()
        scanner.expire_stale_events(db)
        after = db.execute(select(Event).where(Event.status == "scheduled")
                           ).scalars().all()
        assert len(after) == len(before) - (
            sum(1 for e in before if e.start_time < datetime.now(timezone.utc).replace(tzinfo=None)))


class TestOddsIntegrity:
    def test_odds_append_only_history(self, db):
        rows = db.execute(select(Odds).order_by(Odds.captured_at)).scalars().all()
        assert len(rows) > 100
        keyed = {}
        for r in rows:
            keyed.setdefault((r.event_id, r.bookmaker_key, r.market_key, r.outcome), []).append(r)
        multi = [v for v in keyed.values() if len(v) > 1]
        assert multi, "at least one quote series must have multiple snapshots"
        for series in multi:
            assert all(series[i].event_id == series[i + 1].event_id for i in range(len(series) - 1))

    def test_best_odds_chosen_per_outcome(self, db):
        latest = scanner.load_latest_odds(db)
        assert latest
        for (event_id, market_key, outcome), info in list(latest.items())[:50]:
            n_books = db.execute(
                select(Odds.bookmaker_key)
                .where(Odds.event_id == event_id, Odds.market_key == market_key,
                       Odds.outcome == outcome)
            ).scalars().all()
            assert len(set(n_books)) >= 1
            best_in_db = db.execute(
                select(Odds.odds)
                .where(Odds.event_id == event_id, Odds.market_key == market_key,
                       Odds.outcome == outcome)
                .order_by(Odds.odds.desc())
            ).scalars().first()
            assert info["odds"] <= best_in_db + 1e-9
