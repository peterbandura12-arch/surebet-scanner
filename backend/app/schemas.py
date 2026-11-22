from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str
    version: str
    demo_mode: bool
    database: str
    cache: str
    simulated_data: bool


class CalcLegIn(BaseModel):
    outcome: str = Field(min_length=1, max_length=40)
    odds: float = Field(gt=1.0, description="Decimal odds, must be > 1.0")


class CalcRequest(BaseModel):
    odds: list[CalcLegIn] = Field(min_length=2, max_length=20)
    bankroll: float = Field(default=1000.0, gt=0, le=10_000_000)
    fee_pct: float = Field(default=0.0, ge=0, le=50)
    stake_step: float = Field(default=0.01, gt=0, le=100)
    rounding_mode: Literal["floor", "nearest"] = "floor"


class CalculatorRequest(BaseModel):
    event_id: str | None = None
    market_key: str | None = None
    bankroll: float = Field(default=1000.0, gt=0)


class PaperPlaceRequest(BaseModel):
    portfolio_id: str
    opportunity_id: str
    total_stake: float = Field(gt=0, le=10_000_000)


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    starting_bankroll: float = Field(gt=0, le=10_000_000)
    currency: str = "EUR"


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    event_type: Literal["new_opportunity", "roi_threshold", "opportunity_expired",
                        "odds_changed", "source_unavailable"]
    threshold_roi: float | None = None
    sport_key: str | None = None
    channel: Literal["in_app", "telegram_future"] = "in_app"
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None
    threshold_roi: float | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)


class ManualMatchUpdate(BaseModel):
    event_id: str | None = None
    action: Literal["accept", "reject", "relink"]
