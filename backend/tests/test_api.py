"""API integration tests against the FastAPI app (demo database)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client(demo_db):
    app = create_app()
    with TestClient(app) as c:
        yield c


def _scanner_results(r):
    body = r.json()
    return body["results"] if isinstance(body, dict) else body


def _active_opp_id(client) -> str | None:
    r = client.get("/api/opportunities", params={"status": "active", "limit": 1})
    items = r.json()["results"] if isinstance(r.json(), dict) else r.json()
    return items[0]["id"] if items else None


class TestSystem:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["simulated_data"] is True

    def test_meta_and_sports(self, client):
        assert client.get("/api/meta").status_code == 200
        r = client.get("/api/sports")
        assert r.status_code == 200
        sports = r.json()
        assert len(sports) >= 10
        keys = {s["key"] for s in sports}
        assert {"football", "basketball", "tennis"} <= keys

    def test_bookmakers(self, client):
        r = client.get("/api/bookmakers")
        assert r.status_code == 200
        assert len(r.json()) >= 8

    def test_sources_flagged_simulated(self, client):
        r = client.get("/api/sources")
        assert r.status_code == 200
        sources = r.json()
        assert any(s["type"] == "demo" and "simulated" in s["name"].lower()
                   for s in sources)
        for src in sources:
            if src["type"] == "real":
                assert src["status"] != "active", (
                    "real provider must not run without configured credentials")

    def test_settings_roundtrip(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        keys = list(r.json())
        assert keys, "seeded settings must exist"

    def test_settings_update_via_query_params(self, client):
        keys = list(client.get("/api/settings").json())
        key = keys[0]
        r = client.put(f"/api/settings?key={key}&value=2.5",
                       headers={"content-type": "application/json"})
        assert r.status_code == 200
        assert r.json()["key"] == key
        assert client.get("/api/settings").json()[key]["value"] == 2.5

    def test_settings_update_keeps_text_as_string(self, client):
        keys = list(client.get("/api/settings").json())
        key = keys[0]
        r = client.put(f"/api/settings?key={key}&value=abc", headers={})
        assert r.status_code == 200
        assert client.get("/api/settings").json()[key]["value"] == "abc"

    def test_settings_update_unknown_key(self, client):
        r = client.put("/api/settings?key=n_a&value=1")
        assert r.status_code == 404


class TestDashboardAndAnalytics:
    def test_dashboard(self, client):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert d["demo_mode"] is True
        totals = d["totals"]
        assert totals["opportunities_total"] > 0
        assert totals["opportunities_active"] > 0
        for field in ("avg_active_roi_pct", "max_roi_pct", "monitored_events",
                      "monitored_sports", "virtual_capital"):
            assert field in totals
        assert d["by_sport"] and d["by_bookmaker"]
        assert d["recent_opportunities"]

    def test_analytics_endpoints(self, client):
        for path in ("/api/analytics/opportunities-over-time",
                     "/api/analytics/roi-distribution",
                     "/api/analytics/roi-by-sport",
                     "/api/analytics/roi-by-bookmaker",
                     "/api/analytics/opportunity-lifetime",
                     "/api/analytics/detected-vs-expired"):
            r = client.get(path)
            assert r.status_code == 200, path

    def test_portfolio_curve(self, client):
        r = client.get("/api/analytics/portfolio-curve")
        assert r.status_code == 200


class TestScanner:
    def test_scanner_lists_opportunities(self, client):
        r = client.get("/api/scanner")
        assert r.status_code == 200
        body = r.json()
        results = body["results"] if isinstance(body, dict) else body
        assert results

    def test_scanner_min_roi_filter(self, client):
        r = client.get("/api/scanner", params={"min_roi": 1.0})
        assert r.status_code == 200
        for o in _scanner_results(r):
            assert o["roi_pct"] >= 1.0

    def test_scanner_sport_filter(self, client):
        r = client.get("/api/scanner", params={"sport": "football"})
        assert r.status_code == 200
        for o in _scanner_results(r):
            assert o["sport"] == "football"

    def test_opportunity_detail(self, client):
        oid = _active_opp_id(client)
        if not oid:
            pytest.skip("no active opportunities in demo state")
        detail = client.get(f"/api/opportunities/{oid}")
        assert detail.status_code == 200
        assert detail.json()["id"] == oid

    def test_opportunity_history(self, client):
        r = client.get("/api/opportunities", params={"days": 7})
        assert r.status_code == 200


class TestEvents:
    def test_events_list(self, client):
        r = client.get("/api/events")
        assert r.status_code == 200
        body = r.json()
        items = body["results"] if isinstance(body, dict) else body
        assert items

    def test_event_detail_with_odds(self, client):
        body = client.get("/api/events").json()
        items = body["results"] if isinstance(body, dict) else body
        ev = items[0]
        r = client.get(f"/api/events/{ev['id']}")
        assert r.status_code == 200

    def test_matching_review(self, client):
        r = client.get("/api/matching/review")
        assert r.status_code == 200


class TestCalculator:
    def test_two_way_arb(self, client):
        r = client.post("/api/calc", json={
            "odds": [{"outcome": "home", "odds": 2.10},
                     {"outcome": "away", "odds": 2.05}],
            "bankroll": 1000})
        assert r.status_code == 200
        body = r.json()
        assert body["is_arbitrage"] is True
        assert body["roi_pct"] == pytest.approx(3.731, abs=0.02)

    def test_no_arb(self, client):
        r = client.post("/api/calc", json={
            "odds": [{"outcome": "home", "odds": 1.50},
                     {"outcome": "away", "odds": 2.50}],
            "bankroll": 1000})
        assert r.status_code == 200
        assert r.json()["is_arbitrage"] is False

    def test_invalid_odds_rejected(self, client):
        r = client.post("/api/calc", json={
            "odds": [{"outcome": "home", "odds": 1.0},
                     {"outcome": "away", "odds": 2.0}]})
        assert r.status_code == 422

    def test_negative_odds_rejected(self, client):
        r = client.post("/api/calc", json={
            "odds": [{"outcome": "home", "odds": -2.0},
                     {"outcome": "away", "odds": 2.0}]})
        assert r.status_code == 422

    def test_single_outcome_rejected(self, client):
        r = client.post("/api/calc", json={
            "odds": [{"outcome": "home", "odds": 2.0}]})
        assert r.status_code == 422


class TestPaperTrading:
    def test_portfolio_defaults(self, client):
        r = client.get("/api/paper/portfolio")
        assert r.status_code == 200
        body = r.json()
        assert body.get("portfolio", body).get("is_simulated") is True

    def test_place_position_flow(self, client):
        opp_id = _active_opp_id(client)
        if not opp_id:
            pytest.skip("no active opportunities in demo state")
        pf = client.post("/api/paper/portfolios", json={
            "name": "API Test", "starting_bankroll": 5000}).json()
        pf_id = pf["id"]
        r = client.post("/api/paper/positions", json={
            "portfolio_id": pf_id,
            "opportunity_id": opp_id,
            "total_stake": 100})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "open"

    def test_place_position_insufficient_balance(self, client):
        opp_id = _active_opp_id(client)
        if not opp_id:
            pytest.skip("no active opportunities in demo state")
        pf = client.post("/api/paper/portfolios", json={
            "name": "API Poor", "starting_bankroll": 10}).json()
        r = client.post("/api/paper/positions", json={
            "portfolio_id": pf["id"],
            "opportunity_id": opp_id,
            "total_stake": 5000})
        assert r.status_code == 400
        assert "insufficient" in r.json()["detail"].lower()

    def test_place_position_rejects_bad_stake(self, client):
        opp_id = _active_opp_id(client)
        if not opp_id:
            pytest.skip("no active opportunities in demo state")
        r = client.post("/api/paper/positions", json={
            "portfolio_id": "test-pf",
            "opportunity_id": opp_id,
            "total_stake": -10})
        assert r.status_code == 422

    def test_settle_endpoint(self, client):
        r = client.post("/api/paper/settle")
        assert r.status_code == 200
        assert r.json()["simulated"] is True


class TestAlerts:
    def test_rules_crud(self, client):
        r = client.post("/api/alerts/rules", json={
            "name": "High ROI", "event_type": "roi_threshold",
            "threshold_roi": 2.0})
        assert r.status_code in (200, 201)
        rules = client.get("/api/alerts/rules").json()
        assert any(rule["name"] == "High ROI" for rule in rules)
        notifications = client.get("/api/alerts/notifications").json()
        assert isinstance(notifications, dict)
        assert "results" in notifications

    def test_invalid_rule_rejected(self, client):
        r = client.post("/api/alerts/rules", json={
            "name": "", "event_type": "roi_threshold"})
        assert r.status_code == 422


class TestWebsocket:
    def test_ws_hello(self, client):
        with client.websocket_connect("/ws/live") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "hello"
            assert msg["simulated"] is True
            ws.send_text("ping")
            assert ws.receive_json()["type"] == "pong"
