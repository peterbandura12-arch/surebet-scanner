"""Initial seeding of reference data (all DEMO/simulated)."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import markets as mc
from app.models import (AlertRule, Bookmaker, DataSource, Market, Portfolio,
                        Sport, SystemSetting)
from app.services.providers.demo import BOOKMAKERS

log = logging.getLogger(__name__)

DEFAULT_DATA_SOURCES = [
    {"key": "demo-a", "name": "Demo Feed A (simulated)", "type": "demo",
     "note": "Simulated odds feed used for the demo environment."},
    {"key": "demo-b", "name": "Demo Feed B (simulated, renamed events)",
     "type": "demo",
     "note": "Simulated feed with different event naming to exercise the matching engine."},
    {"key": "theoddsapi", "name": "The Odds API", "type": "real",
     "requires_api_key": True, "docs_url": "https://the-odds-api.com/liveapi/guides/v4/",
     "note": "Optional real provider. Enable by setting THEODDSAPI_KEY in the backend .env."},
]


def seed(session: Session) -> None:
    for key, meta in mc.SPORTS.items():
        if session.execute(select(Sport).where(Sport.key == key)).scalar_one_or_none() is None:
            session.add(Sport(key=key, name=meta["name"], icon=meta["icon"]))

    for m in mc.MARKETS.values():
        if session.get(Market, m.key + ":" + m.sport) is None:
            session.add(Market(key=f"{m.key}:{m.sport}", name=m.name,
                               sport_key=m.sport, category=m.category,
                               outcomes=list(m.outcomes),
                               settlement_note=m.settlement_note))

    for key, _margin in BOOKMAKERS:
        if session.execute(select(Bookmaker).where(Bookmaker.key == key)).scalar_one_or_none() is None:
            session.add(Bookmaker(key=key, name=key, is_demo=True))

    for src in DEFAULT_DATA_SOURCES:
        if session.get(DataSource, src["key"]) is None:
            session.add(DataSource(key=src["key"], name=src["name"],
                                   type=src.get("type", "demo"),
                                   requires_api_key=src.get("requires_api_key", False),
                                   docs_url=src.get("docs_url", ""),
                                   note=src.get("note", ""),
                                   status="active" if src["type"] == "demo" else "inactive"))

    if session.execute(select(Portfolio)).scalars().first() is None:
        session.add(Portfolio(name="Demo Portfolio", currency="EUR",
                              starting_bankroll=10000.0, balance=10000.0,
                              is_simulated=True))

    if session.execute(select(AlertRule)).scalars().first() is None:
        session.add(AlertRule(name="New arbitrage detected",
                              event_type="new_opportunity", channel="in_app"))
        session.add(AlertRule(name="ROI above 2%",
                              event_type="roi_threshold", threshold_roi=2.0,
                              channel="in_app"))
        session.add(AlertRule(name="Opportunity expired",
                              event_type="opportunity_expired", channel="in_app"))

    defaults = {
        "min_roi_pct": get_settings().min_roi_pct,
        "odds_max_age_seconds": get_settings().odds_max_age_seconds,
        "default_bankroll": 1000.0,
        "fee_pct": 0.0,
        "stake_step": 0.01,
        "demo_mode": True,
    }
    for key, value in defaults.items():
        if session.get(SystemSetting, key) is None:
            session.add(SystemSetting(key=key, value=value,
                                      description="Default (editable in Settings)"))
    session.commit()
    log.info("seed complete")
