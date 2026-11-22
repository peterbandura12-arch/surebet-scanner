import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

TEST_DB = os.path.join(BACKEND_DIR, "test_surebet.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["FEED_AUTOSTART"] = "0"

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def demo_db():
    """Seed a deterministic demo universe (one feed tick) for service tests."""
    import app.models  # noqa: F401
    from app.db import Base, SessionLocal, engine
    from app.seed import seed
    from app.jobs import runner

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    seed(s)
    s.close()
    runner.tick_once()
    yield


@pytest.fixture()
def db(demo_db):
    from app.db import SessionLocal
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()
