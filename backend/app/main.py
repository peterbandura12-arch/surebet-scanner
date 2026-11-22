"""Surebet Scanner API — FastAPI application."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app.seed import seed
from app.api.routes import (alerts, dashboard, events, paper, scanner, system)
from app.api.routes import ws as ws_routes

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.jobs import runner
    Base.metadata.create_all(bind=engine)
    from app.db import SessionLocal
    session = SessionLocal()
    try:
        seed(session)
    finally:
        session.close()
    if get_settings().feed_autostart:
        await asyncio.to_thread(runner.tick_once)
        runner.start()
    yield
    await runner.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version,
                  lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(system.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(scanner.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(paper.router, prefix="/api")
    app.include_router(alerts.router, prefix="/api")
    app.include_router(ws_routes.router)
    return app


app = create_app()
