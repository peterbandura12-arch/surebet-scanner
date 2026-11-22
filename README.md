# SUREBET SCANNER — Demo Edition

Professional sports-odds arbitrage analysis platform operating entirely in
**DEMO / PAPER-TRADING mode**. All odds, opportunities and portfolio results
are produced by deterministic simulated feeds — no real-money betting, no
automated bet placement, and no fabricated "real" statistics.

![status](https://img.shields.io/badge/mode-DEMO-yellow) — every page and API
response is explicitly labelled as simulated.

## What it does

- **Live scanner** groups the freshest odds per (event, exact market with line),
  resolves best odds per outcome across 11 simulated bookmakers and detects
  arbitrage when `S = Σ(1/oddsᵢ) < 1`.
- **Math engine** computes theoretical ROI `(1/S − 1)·100`, optimal equal-payout
  stakes `B·(1/oddsᵢ)/S`, exchange-fee adjustment (commission on net winnings),
  and conservative rounding — never exceeding the bankroll.
- **Strict market compatibility**: a football 1X2 is never compared with double
  chance, Asian handicap lines, or totals with different lines; market keys are
  sport-scoped (`h2h` = 1X2 in football, 2-way moneyline in basketball).
- **Event matching** normalises team names ("Manchester City vs Arsenal" ≡
  "Arsenal - Manchester City"), combines participant (direct + reversed),
  league and kick-off signals into a confidence score with a manual review queue.
- **Demo data engine**: two independent simulated feeds ("demo-a" canonical,
  "demo-b" with variant names/times) drift odds every few seconds; the scanner
  *discovers* opportunities from this raw data — nothing is precomputed.
- **Paper trading**: virtual portfolios, simulated positions split across legs,
  deterministic simulated settlement (win/void/loss) after kick-off.
- **Analytics**: opportunities over time, ROI distribution, ROI by sport and
  bookmaker, opportunity lifetime, portfolio curve — all computed from stored
  demo data.
- **Alerts**: rules (new opportunity, ROI threshold, expiry, odds change, source
  unavailable) with in-app notifications; Telegram is an inert stub.
- **Provider architecture**: abstract `OddsProvider` with a demo provider and a
  real implementation for The Odds API (enabled only when its env key exists).

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4, Recharts, lucide-react |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 |
| Data | PostgreSQL (production) / SQLite (local default), Redis optional cache |
| Realtime | WebSockets (`/ws/live`) |
| Packaging | Docker, Docker Compose |
| Quality | Pytest (97 tests), `next build` + `tsc --noEmit`, Alembic migrations |

## Quick start (local, no Docker)

```bash
# 1. Backend (SQLite by default; no external services needed)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
# API: http://localhost:8000/api/health  (demo seed + first scan run automatically)

# 2. Frontend
cd ../frontend
npm install
cp .env.example .env.local
npm run dev
# UI: http://localhost:3000
```

With PostgreSQL/Redis, export `DATABASE_URL` / `REDIS_URL` before starting the
API (see `.env.example`). To use migrations instead of auto-created tables:
`alembic upgrade head`.

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
# UI: http://localhost:3000  API: http://localhost:8000
```

## Tests & verification

```bash
cd backend && python3 -m pytest tests -q        # 97 passed
cd frontend && npm run build && npm run typecheck
```

Independent math check:

```python
from app.core.arbitrage import compute_arbitrage
r = compute_arbitrage([2.10, 2.05], ["home", "away"], 1000)
print(r.is_arbitrage, round(r.roi_pct, 2), [l.stake for l in r.legs])
# True, 3.73 (approx), equalised payouts
```

## Documentation

- [docs/architecture.md](docs/architecture.md) — modules, data flow, matching, DB model
- [docs/running.md](docs/running.md) — detailed run/deploy configuration
- [docs/limitations.md](docs/limitations.md) — demo boundaries & safety rules

## Safety

- No real-money betting. No automated bet placement. Ever.
- All demo data is labelled simulated at API level (`"simulated": true`),
  in the UI ("DEMO MODE" badge, disclaimers) and in logs.
- External provider keys live only in environment variables; a missing key
  disables the provider — fake data is never a substitute for real feeds.
- The backend exposes rate-limited mutating endpoints and validated request
  schemas; API keys are never surfaced to the frontend.
