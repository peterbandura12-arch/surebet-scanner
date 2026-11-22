"""Alert engine: pluggable notification channels.

``in_app`` notifications are fully implemented. A Telegram channel stub is
provided as an *architecture placeholder* — it is never activated without
credentials configured via environment variables (demo doesn't require it).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AlertRule, Notification

log = logging.getLogger(__name__)

EVENT_TYPES = ("new_opportunity", "roi_threshold", "opportunity_expired",
               "odds_changed", "source_unavailable")


@dataclass
class AlertPayload:
    event_type: str
    title: str
    body: str = ""
    payload: dict | None = None


class NotificationChannel:
    key = "in_app"

    def deliver(self, payload: AlertPayload) -> bool:
        return True


class FutureTelegramChannel(NotificationChannel):
    """Placeholder for a future Telegram integration.

    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env variables. Never
    activated in demo mode."""
    key = "telegram_future"

    def deliver(self, payload: AlertPayload) -> bool:
        import os
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat:
            log.info("telegram channel skipped (not configured): %s", payload.title)
            return False
        log.info("telegram channel would deliver: %s", payload.title)
        return False


_CHANNELS = {NotificationChannel.key: NotificationChannel(),
             FutureTelegramChannel.key: FutureTelegramChannel()}


def get_channel(key: str) -> NotificationChannel:
    return _CHANNELS.get(key, _CHANNELS["in_app"])


def dispatch(session: Session, payload: AlertPayload) -> list[Notification]:
    rules = session.execute(
        select(AlertRule).where(AlertRule.enabled == True,  # noqa: E712
                                AlertRule.event_type == payload.event_type)
    ).scalars().all()
    created = []
    for rule in rules:
        if payload.event_type == "roi_threshold":
            payload_roi = (payload.payload or {}).get("roi_pct", 0)
            if rule.threshold_roi is not None and payload_roi < rule.threshold_roi:
                continue
        if rule.sport_key and (payload.payload or {}).get("sport") != rule.sport_key:
            continue
        channel = get_channel(rule.channel)
        if not channel.deliver(payload):
            continue
        note = Notification(alert_rule_id=rule.id, event_type=payload.event_type,
                            title=payload.title, body=payload.body,
                            payload=payload.payload or {}, channel=rule.channel)
        session.add(note)
        created.append(note)
    if created:
        session.flush()
    return created


def serialize_notification(n: Notification) -> dict:
    return {
        "id": n.id,
        "event_type": n.event_type,
        "title": n.title,
        "body": n.body,
        "payload": n.payload,
        "read": n.read,
        "channel": n.channel,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }
