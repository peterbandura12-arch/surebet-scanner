from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws import manager

log = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_json({"type": "hello", "simulated": True,
                            "message": "Demo feed updates will stream here."})
        while True:
            data = await ws.receive_text()
            if data in ("ping", ""):
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
        log.debug("websocket client disconnected with error", exc_info=True)
