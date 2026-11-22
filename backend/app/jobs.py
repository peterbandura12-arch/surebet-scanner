"""Background loop: feed ticks -> scan -> persist -> alert -> settle -> broadcast."""
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from app.config import get_settings
from app.services import alerts, paper, scanner
from app.services.feed import FeedManager
from app.ws import manager

log = logging.getLogger(__name__)


class BackgroundRunner:
    def __init__(self) -> None:
        self.feed = FeedManager()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.last_scan: dict = {}
        self.ticks = 0

    async def run_loop(self) -> None:
        s = get_settings()
        log.info("background feed loop started (interval=%ss)", s.feed_tick_seconds)
        # first tick synchronously so data is available immediately on startup
        try:
            await asyncio.to_thread(self.tick_once)
        except Exception:
            log.exception("initial tick failed")
        while not self._stop.is_set():
            try:
                payload = await asyncio.to_thread(self.tick_once)
                if payload:
                    await manager.broadcast(payload)
            except Exception:
                log.exception("tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(),
                                       timeout=max(s.feed_tick_seconds, 1))
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

    def tick_once(self) -> dict | None:
        from app.db import SessionLocal
        session = SessionLocal()
        scan = {"new": [], "updated": [], "expired": []}
        try:
            summary = self.feed.tick(session)
            scanner.expire_stale_events(session)
            scan = scanner.persist_scan(session)
            self.ticks += 1

            for opp in scan["new"]:
                alerts.dispatch(session, alerts.AlertPayload(
                    event_type="new_opportunity",
                    title=f"New surebet: {opp['event_name']} ({opp['roi_pct']:.2f}% ROI)",
                    body=f"{opp['market_name']} — profit {(1/opp['sum_inverse']-1)*100:.2f}%",
                    payload={**opp, "roi_pct": opp["roi_pct"]}))
            for opp in scan["new"]:
                alerts.dispatch(session, alerts.AlertPayload(
                    event_type="roi_threshold",
                    title=f"High ROI opportunity: {opp['roi_pct']:.2f}%",
                    body=opp["event_name"],
                    payload=opp))
            for opp in scan["expired"]:
                alerts.dispatch(session, alerts.AlertPayload(
                    event_type="opportunity_expired",
                    title=f"Opportunity expired: {opp['event_name']}",
                    body=opp["market_name"],
                    payload=opp))
            settled = paper.settle_due_positions(session)
            session.commit()
            self.last_scan = {
                "scan": {k: (len(v) if isinstance(v, list) else v)
                          for k, v in scan.items()},
                "feed": {k: (len(v) if isinstance(v, list) else v)
                          for k, v in summary.items() if k != "matches"},
                "settled_positions": len(settled),
                "tick": self.ticks,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        return {
            "type": "scan_update",
            "new": scan["new"],
            "updated": scan["updated"][:10],
            "expired": [{**o, "legs": []} for o in scan["expired"][:10]],
            "stats": self.last_scan,
            "simulated": True,
        }

    def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self.run_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            with suppress(asyncio.CancelledError):
                await self._task


runner = BackgroundRunner()
