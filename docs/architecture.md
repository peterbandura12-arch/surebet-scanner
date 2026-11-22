# Architecture

## High-level data flow

```
DemoOddsProvider (demo-a)  ─┐
DemoOddsProvider (demo-b)  ─┤→ FeedManager.tick ─→ Event matching ─→ Odds (append-only)
TheOddsApiProvider (opt.)  ─┘                                   │
                                                                ▼
                                  Scanner (group by event+market, best odds/outcome)
                                                                │
                        ┌───────────────────────────────────────┤
                        ▼                     ▼                 ▼
                  Opportunities      Alert dispatch      Paper settlement
                        │
                        ▼
        PostgreSQL / SQLite (17 domain models)
                        │
                        ▼
           FastAPI REST (/api/…) + WS (/ws/live)
                        │
                        ▼
              Next.js dashboard (11 pages)
```

The background runner (`app/jobs.py`) executes one tick per
`FEED_TICK_SECONDS`: `feed.tick → expire_stale_events → persist_scan →
alerts.dispatch → settle_due_positions → commit → WS broadcast`.

## Backend modules (`backend/app/`)

| Module | Responsibility |
|---|---|
| `core/arbitrage.py` | Pure math engine: `sum_inverse`, validation, `compute_arbitrage` with fees, rounding modes, notes |
| `core/markets.py` | Sport-scoped market catalogue (`MARKETS[(sport, key)]`), 12 sports, settlement rules |
| `core/normalize.py` | Accent stripping, alias/abbreviation map, stopword removal for participants and leagues |
| `core/matching.py` | Multi-signal event matching; accept ≥ 0.82, review band 0.55–0.82 |
| `models.py` | SQLAlchemy ORM models (users, sports, leagues, teams, players, events, event_matches, bookmakers, markets, odds, opportunities, opportunity_snapshots, alert_rules, notifications, portfolios, positions, system_settings, data_sources) |
| `db.py` | Engine (SQLite WAL/FK/busy_timeout when SQLite), sessions, MemoryCache/RedisCache |
| `services/providers/` | `OddsProvider` ABC, `DemoOddsProvider` (deterministic seeds, margins per bookmaker, slow-book artefacts), `TheOddsApiProvider` (real, key-gated, throttled) |
| `services/feed.py` | Upserts canonical events, matches provider events, stores append-only odds with movement tracking |
| `services/scanner.py` | Freshness window, two-stage best-odds resolution, strict market grouping, opportunity reconciliation (active/expired + snapshots) |
| `services/paper.py` | Virtual portfolios, stake splitting, deterministic settlement |
| `services/alerts.py` | Pluggable channels, in-app notifications, inert Telegram stub |
| `services/analytics.py`, `dashboard.py` | Aggregations computed from stored data only |
| `api/routes/` | system, dashboard, scanner, events (+matching review), paper, alerts, ws |
| `ws/manager.py` | ConnectionManager broadcast fan-out |

## Guarantee: scanner discovers, never receives, opportunities

The demo provider only emits **raw odds quotes** (with deliberate noise: bad
margins, slow-book lags, occasional stale/incomplete markets). Arbitrage emerges
only when the scanner finds, across bookmakers, a set of best odds whose inverse
sum is < 1. Seeded RNG makes the whole universe reproducible (`DEMO_SEED`).

## Frontend structure (`frontend/`)

- `app/` — 11 route pages (App Router, client-side data fetching with polling)
- `components/providers/live.tsx` — WebSocket context with exponential reconnect
- `components/ui/primitives.tsx` — shadcn-style primitives (Card, Badge, Button, Input, Select, StatCard…)
- `components/charts.tsx` — Recharts wrappers
- `lib/api.ts` — typed REST client, `lib/types.ts` — shared contracts

## Database

UTC timestamps everywhere; the odds table is append-only with a
`previous_odds/open_odds` movement chain; opportunity snapshots record ROI over
time for charts; indexes on hot filter columns (event_id, bookmaker_key,
market_key, status, sport_key, detected_at).

Migrations: `backend/alembic/` (`alembic upgrade head`). Locally without
PostgreSQL, `create_all` also produces the identical schema at startup, which
keeps the demo zero-configuration.
