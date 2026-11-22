"""Abstract data provider interface.

Every data source (demo or real) implements this contract. Real providers
must only use documented, authorized APIs with keys supplied via environment
variables, and must never fabricate data when the upstream request fails.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger(__name__)


@dataclass
class ProviderOdds:
    external_event_id: str
    bookmaker_key: str
    market_key: str
    outcome: str
    odds: float
    captured_at: datetime
    is_stale: bool = False


@dataclass
class ProviderEvent:
    provider: str
    external_id: str
    sport: str
    league: str
    league_country: str = ""
    home_name: str = ""
    away_name: str = ""
    start_time: datetime | None = None
    status: str = "scheduled"
    odds: list[ProviderOdds] = field(default_factory=list)


@dataclass
class PullResult:
    events: list[ProviderEvent]
    is_simulated: bool
    warnings: list[str] = field(default_factory=list)


class OddsProvider(ABC):
    key: str
    name: str
    is_simulated: bool = False
    requires_api_key: bool = False
    docs_url: str = ""

    @abstractmethod
    def pull(self) -> PullResult: ...

    def health(self) -> dict:
        return {"provider": self.key, "ok": True, "simulated": self.is_simulated}


class ProviderNotConfigured(RuntimeError):
    """Raised when a real provider is enabled without credentials/env config."""
