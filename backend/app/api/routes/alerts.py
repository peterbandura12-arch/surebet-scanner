from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.system import rate_limit
from app.db import get_db
from app.models import AlertRule, Notification
from app.schemas import AlertRuleCreate, AlertRuleUpdate
from app.services import alerts as alerts_service

router = APIRouter(tags=["alerts"])


@router.get("/alerts/rules")
def list_rules(db: Session = Depends(get_db)):
    return [{
        "id": r.id, "name": r.name, "event_type": r.event_type,
        "threshold_roi": r.threshold_roi, "sport_key": r.sport_key,
        "channel": r.channel, "enabled": r.enabled,
    } for r in db.execute(select(AlertRule)).scalars()]


@router.post("/alerts/rules", dependencies=[Depends(rate_limit())])
def create_rule(body: AlertRuleCreate, db: Session = Depends(get_db)):
    if body.event_type not in alerts_service.EVENT_TYPES:
        raise HTTPException(400, "unknown event type")
    rule = AlertRule(name=body.name, event_type=body.event_type,
                     threshold_roi=body.threshold_roi, sport_key=body.sport_key,
                     channel=body.channel, enabled=body.enabled)
    db.add(rule)
    db.commit()
    return {"id": rule.id, "name": rule.name}


@router.patch("/alerts/rules/{rule_id}", dependencies=[Depends(rate_limit())])
def update_rule(rule_id: str, body: AlertRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(404, "rule not found")
    if body.enabled is not None:
        rule.enabled = body.enabled
    if body.threshold_roi is not None:
        rule.threshold_roi = body.threshold_roi
    if body.name is not None:
        rule.name = body.name
    db.commit()
    return {"id": rule.id, "enabled": rule.enabled,
            "threshold_roi": rule.threshold_roi}


@router.get("/alerts/notifications")
def notifications(limit: int = 100, unread_only: bool = False,
                  db: Session = Depends(get_db)):
    q = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    if unread_only:
        q = q.where(Notification.read == False)  # noqa: E712
    rows = db.execute(q).scalars().all()
    unread = db.execute(
        select(Notification).where(Notification.read == False)).scalars().all()  # noqa: E712
    return {"count": len(rows), "unread": len(unread),
            "results": [alerts_service.serialize_notification(n) for n in rows]}


@router.post("/alerts/notifications/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None:
        raise HTTPException(404, "notification not found")
    n.read = True
    db.commit()
    return {"id": n.id, "read": True}


@router.post("/alerts/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db)):
    rows = db.execute(select(Notification).where(Notification.read == False)).scalars().all()  # noqa: E712
    for n in rows:
        n.read = True
    db.commit()
    return {"marked": len(rows)}
