from __future__ import annotations

import json
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (Bookmaker, DataSource, Sport, SystemSetting)
from app.schemas import Health

router = APIRouter(tags=["system"])
_rate: dict[str, list[float]] = defaultdict(list)


def rate_limit(max_calls: int = 60, window: float = 60.0):
    """Simple in-memory rate limiting for mutating endpoints."""

    def dependency() -> None:
        key = "global"
        now = time.time()
        bucket = [t for t in _rate[key] if now - t < window]
        if len(bucket) >= max_calls:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        bucket.append(now)
        _rate[key] = bucket

    return dependency


@router.get("/health", response_model=Health)
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    db_ok = True
    try:
        db.execute(select(Sport).limit(1))
    except Exception:
        db_ok = False
    return Health(
        status="ok" if db_ok else "degraded",
        version=settings.app_version,
        demo_mode=settings.demo_mode,
        database="connected" if db_ok else "error",
        cache="redis" if settings.redis_url else "in-memory",
        simulated_data=True,
    )


@router.get("/meta")
def meta():
    return {
        "app": "Surebet Scanner",
        "demo_mode": True,
        "simulated_data": True,
        "disclaimer": ("All data in this demo environment is SIMULATED. "
                       "No real-money betting is possible."),
    }


@router.get("/sports")
def list_sports(db: Session = Depends(get_db)):
    return [{"key": s.key, "name": s.name, "enabled": s.enabled}
            for s in db.execute(select(Sport).order_by(Sport.name)).scalars()]


@router.get("/sports/{sport_key}/markets")
def sport_markets(sport_key: str, db: Session = Depends(get_db)):
    from app.core import markets as mc
    if mc.SPORTS.get(sport_key) is None:
        raise HTTPException(404, "unknown sport")
    return [{
        "key": m.key, "name": m.name, "category": m.category,
        "outcomes": list(m.outcomes), "settlement_note": m.settlement_note,
    } for m in mc.markets_for_sport(sport_key)]


@router.get("/bookmakers")
def list_bookmakers(db: Session = Depends(get_db)):
    return [{"key": b.key, "name": b.name, "is_demo": b.is_demo,
             "active": b.active}
            for b in db.execute(select(Bookmaker).order_by(Bookmaker.name)).scalars()]


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    out = []
    for src in db.execute(select(DataSource)).scalars():
        out.append({
            "key": src.key, "name": src.name, "type": src.type,
            "status": src.status, "enabled": src.enabled,
            "requires_api_key": src.requires_api_key,
            "docs_url": src.docs_url, "note": src.note,
            "last_sync_at": src.last_sync_at.isoformat() if src.last_sync_at else None,
            "last_error": src.last_error,
        })
    return out


@router.get("/settings")
def get_settings_route(db: Session = Depends(get_db)):
    return {s.key: {"value": s.value, "description": s.description}
            for s in db.execute(select(SystemSetting)).scalars()}


@router.put("/settings", dependencies=[Depends(rate_limit())])
def update_setting(key: str = Query(...), value: str = Query(...),
                   db: Session = Depends(get_db)):
    setting = db.get(SystemSetting, key)
    if setting is None:
        raise HTTPException(404, "unknown setting")
    try:
        parsed = json.loads(value)
        setting.value = parsed if isinstance(parsed, (dict, list, str, int, float, bool)) else value
    except (ValueError, TypeError):
        setting.value = value
    db.commit()
    return {"key": key, "value": setting.value}
