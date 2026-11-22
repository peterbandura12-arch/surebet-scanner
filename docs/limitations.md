# Known limitations & demo boundaries

1. **Everything is simulated.** The demo feeds generate synthetic quotes from
   deterministic seeds. No number in the UI represents real bookmaker prices or
   real returns. Analysing real arbitrage edges with this demo data would be
   meaningless by design.
2. **No real-money betting.** There is no payment, wallet or bookmaker
   integration capable of placing bets anywhere in the codebase. Paper trading
   results are simulated ("virtual") and always labelled as such.
3. **External providers require credentials.** `TheOddsApiProvider` is fully
   implemented (key from `THEODDSAPI_KEY`, throttling, 429/error handling,
   `x-requests-*` budget headers) but disabled without a key. Sportradar /
   API-SPORTS slots follow the same abstract interface; adding one is a single
   provider class. The system never substitutes fake data when a real provider
   fails — it marks the source unavailable.
4. **Docker Compose plugin availability.** The sandbox used for development has
   Docker without the `compose` plugin; the Compose file is YAML-validated but
   was not executed end-to-end inside the sandbox. Local SQLite/uvicorn and
   Next.js runs were executed and verified.
5. **Settlement realism.** Position settlement draws a deterministic result from
   stored odds' implied probabilities — a model, not reality, and it ignores
   correlated outcomes across bookmakers.
6. **Multi-user.** A `users` table exists with password support in the model,
   but the demo does not ship an authentication flow; the API is single-tenant
   local. If exposed, put it behind a reverse proxy with auth.
7. **Scanner window.** Quotes older than `ODDS_MAX_AGE_SECONDS` (default 180 s)
   are excluded and flagged; the background tick refreshes them every
   `FEED_TICK_SECONDS`.
8. **No scraping.** Per policy the project only consumes documented APIs. There
   is deliberately no HTML-scraping fallback.
