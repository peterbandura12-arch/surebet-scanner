from __future__ import annotations

import json
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    s = get_settings()
    url = s.database_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    return engine


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class MemoryCache:
    """Fallback cache used when Redis is not configured (local/demo runs)."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._ttl: dict[str, float] = {}

    def get(self, key: str):
        exp = self._ttl.get(key)
        if exp and exp < time.time():
            self._data.pop(key, None)
            self._ttl.pop(key, None)
            return None
        return self._data.get(key)

    def set(self, key: str, value, ttl: int | None = None):
        self._data[key] = value
        if ttl:
            self._ttl[key] = time.time() + ttl

    def delete(self, key: str):
        self._data.pop(key, None)
        self._ttl.pop(key, None)

    def ping(self) -> bool:
        return True


class RedisCache(MemoryCache):
    """Redis-backed cache with the same tiny interface."""

    def __init__(self, url: str):
        import redis
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._data = {}
        self._ttl = {}

    def get(self, key: str):
        return self._client.get(key)

    def set(self, key: str, value, ttl: int | None = None):
        self._client.set(key, value, ex=ttl)

    def delete(self, key: str):
        self._client.delete(key)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False


def get_cache():
    url = get_settings().redis_url
    if url:
        try:
            return RedisCache(url)
        except Exception:
            pass
    return MemoryCache()


def cache_get_json(cache, key: str, default=None):
    raw = cache.get(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def cache_set_json(cache, key: str, value, ttl: int | None = None):
    cache.set(key, json.dumps(value, default=str), ttl)
