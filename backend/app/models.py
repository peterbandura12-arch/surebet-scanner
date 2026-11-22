from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return uuid.uuid4().hex


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(TimestampMixin,Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(16), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Sport(Base):
    __tablename__ = "sports"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    icon: Mapped[str] = mapped_column(String(40), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class League(TimestampMixin, Base):
    __tablename__ = "leagues"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    sport_key: Mapped[str] = mapped_column(ForeignKey("sports.key"))
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), default="")

    __table_args__ = (UniqueConstraint("sport_key", "key", name="uq_league_sport_key"),)


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    sport_key: Mapped[str] = mapped_column(ForeignKey("sports.key"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(120), index=True)
    league_id: Mapped[str | None] = mapped_column(ForeignKey("leagues.id"), nullable=True)
    country: Mapped[str] = mapped_column(String(80), default="")


class Player(TimestampMixin, Base):
    __tablename__ = "players"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    position: Mapped[str] = mapped_column(String(40), default="")
    jersey: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    sport_key: Mapped[str] = mapped_column(ForeignKey("sports.key"), index=True)
    league_id: Mapped[str | None] = mapped_column(ForeignKey("leagues.id"), nullable=True, index=True)
    home_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    away_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(16), default="scheduled", index=True)
    provider: Mapped[str] = mapped_column(String(40), default="demo")
    external_id: Mapped[str] = mapped_column(String(120), default="")
    match_group: Mapped[str] = mapped_column(String(40), index=True, default="")

    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    league = relationship("League")

    __table_args__ = (Index("ix_events_sport_start", "sport_key", "start_time"),)


class EventMatch(TimestampMixin, Base):
    """Mapping between a provider event description and a canonical event."""
    __tablename__ = "event_matches"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_event_id: Mapped[str] = mapped_column(String(120))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    method: Mapped[str] = mapped_column(String(20), default="auto")
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    manual: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("provider", "external_event_id",
                                       name="uq_provider_external"),)


class Bookmaker(TimestampMixin,Base):
    __tablename__ = "bookmakers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(40), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    commission_pct: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Market(TimestampMixin, Base):
    __tablename__ = "markets"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sport_key: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(40))
    outcomes: Mapped[list] = mapped_column(JSON, default=list)
    settlement_note: Mapped[str] = mapped_column(Text, default="")


class Odds(TimestampMixin, Base):
    """Append-only odds snapshots; never overwritten (history preserved)."""
    __tablename__ = "odds"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_event_id: Mapped[str] = mapped_column(String(120), default="")
    bookmaker_key: Mapped[str] = mapped_column(String(40), index=True)
    market_key: Mapped[str] = mapped_column(String(60), index=True)
    outcome: Mapped[str] = mapped_column(String(40))
    odds: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=utcnow, index=True)
    open_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_odds: Mapped[float | None] = mapped_column(Float, nullable=True)

    event = relationship("Event")

    __table_args__ = (
        Index("ix_odds_group_captured", "event_id", "bookmaker_key", "market_key",
              "outcome", "captured_at"),
    )


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    market_key: Mapped[str] = mapped_column(String(60))
    market_name: Mapped[str] = mapped_column(String(120))
    sport_key: Mapped[str] = mapped_column(String(40), index=True)
    league_name: Mapped[str] = mapped_column(String(120), default="")
    event_name: Mapped[str] = mapped_column(String(255), default="")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    roi_pct: Mapped[float] = mapped_column(Float, index=True)
    sum_inverse: Mapped[float] = mapped_column(Float)
    num_outcomes: Mapped[int] = mapped_column(Integer)
    legs: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_notes: Mapped[list] = mapped_column(JSON, default=list)

    event = relationship("Event")

    __table_args__ = (
        Index("ix_opp_status_roi", "status", "roi_pct"),
        Index("ix_opp_sport_status", "sport_key", "status"),
    )


class OpportunitySnapshot(TimestampMixin,Base):
    __tablename__ = "opportunity_snapshots"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    roi_pct: Mapped[float] = mapped_column(Float)
    legs: Mapped[list] = mapped_column(JSON, default=list)


class AlertRule(TimestampMixin, Base):
    __tablename__ = "alert_rules"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    threshold_roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    sport_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(TimestampMixin,Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    alert_rule_id: Mapped[str | None] = mapped_column(ForeignKey("alert_rules.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")


class Portfolio(TimestampMixin, Base):
    __tablename__ = "portfolios"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    starting_bankroll: Mapped[float] = mapped_column(Float)
    balance: Mapped[float] = mapped_column(Float)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class Position(TimestampMixin, Base):
    """A simulated (paper) bet placed on an opportunity. Never a real bet."""
    __tablename__ = "positions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    event_name: Mapped[str] = mapped_column(String(255), default="")
    market_key: Mapped[str] = mapped_column(String(60))
    market_name: Mapped[str] = mapped_column(String(120), default="")
    sport_key: Mapped[str] = mapped_column(String(40), index=True)
    legs: Mapped[list] = mapped_column(JSON, default=list)
    total_stake: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    payout: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    simulated_result: Mapped[str | None] = mapped_column(String(10), nullable=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_positions_portfolio_status", "portfolio_id", "status"),)


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict | list | str | int | float] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")


class DataSource(TimestampMixin, Base):
    __tablename__ = "data_sources"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(20), default="demo")
    status: Mapped[str] = mapped_column(String(20), default="active")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    docs_url: Mapped[str] = mapped_column(String(255), default="")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
