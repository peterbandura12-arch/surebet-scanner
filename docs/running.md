# Running the project

## 1. Local development (SQLite — zero external services)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

On startup the API:

1. creates the schema (or applies Alembic migration state),
2. seeds the deterministic demo universe (sports, leagues, teams, players,
   bookmakers, system settings, data sources),
3. performs one feed tick (pull quotes, match events, store odds, scan),
4. starts the background loop (`FEED_TICK_SECONDS=5`).

```bash
cd frontend
npm install
cp .env.example .env.local   # points at http://localhost:8000
npm run dev                  # http://localhost:3000
```

## 2. PostgreSQL + Redis

```bash
export DATABASE_URL=postgresql+psycopg://surebet:surebet@localhost:5432/surebet
export REDIS_URL=redis://localhost:6379/0
cd backend && alembic upgrade head
uvicorn app.main:app --port 8000
```

Notes:

- `psycopg` (psycopg3) is required for the `postgresql+psycopg` scheme;
  `psycopg2-binary` also works with `postgresql+psycopg2`.
- Redis is an optional cache layer; leave `REDIS_URL` empty to use the
  in-process cache instead of requiring the service.

## 3. Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Services: `postgres:16`, `redis:7`, `api` (migrations + uvicorn), `frontend`
(Next.js standalone). Frontend public env vars are provided as build args.

## Environment variables (backend)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./surebet.db` | SQLAlchemy URL |
| `REDIS_URL` | *(empty)* | Optional cache |
| `FEED_AUTOSTART` | `1` | Start background loop with the app |
| `FEED_TICK_SECONDS` | `5` | Simulated feed interval |
| `DEMO_SEED` | `20240601` | Deterministic demo RNG seed |
| `MIN_ROI_PCT` | `0.5` | Scanner ROI floor |
| `ODDS_MAX_AGE_SECONDS` | `180` | Freshness window |
| `THEODDSAPI_KEY` | *(empty)* | The Odds API key (real provider stays off if empty) |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed browser origins |

## Health checks

- `GET /api/health` → status, database, cache, `simulated_data: true`
- WS `GET /ws/live` → `{"type": "hello", ...}` frame on connect

## Tests

```bash
cd backend && python3 -m pytest tests -q
cd frontend && npm run build && npm run typecheck
```
