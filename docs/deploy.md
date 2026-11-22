# Deploy na trvalý hosting (bez príkazového riadka)

Celý postup sa dá vykonať z telefónu — všetko sa kliká na webe. Obe platformy
majú bezplatný tier, ktorý pre demo úplne stačí.

## Prehľad

| Súčasť | Platforma | Čo to dostane |
|---|---|---|
| API + demo feed | Render (Web Service) | `https://surebet-api-xxxx.onrender.com` |
| Databáza | Render (PostgreSQL) | pripojená automaticky |
| Frontend | Vercel | `https://surebet-scanner.vercel.app` |

## Krok 1 — kód na GitHube

Repozitár musí byť na GitHube (backend aj frontend v jednom repo). Ak ho
ešte nemáš, vytvor ho na https://github.com/new a kód tam pushni (pomôžem
z tejto relácie — stačí napísať meno repozitára).

## Krok 2 — API + databáza na Renderi

1. Otvor https://dashboard.render.com/select-repo a povoľ prístup k repu.
2. Render nájde **render.yaml** (Blueprint) → klikni **Apply**.
3. Render sa spýta na hodnoty `sync: false`:
   - `CORS_ORIGINS` — najprv prakticky zvoľ `*`, neskôr nahraď URL frontendu,
   - `THEODDSAPI_KEY` — nech prázdne (demo režim),
   - `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` — doplň po kroku 3.
4. Počkaj na deploy; kontrola: `https://<render-url>/api/health` →
   `{"status": "ok", "simulated_data": true}`.

> ⚠️ Free plan Renderu uspí neaktívne služby (~15 min); prvé načítanie trvá
> potom ~30–60 s (demo seed sa spúšťa pri štarte).

## Krok 3 — Frontend na Verceli

1. Otvor https://vercel.com/new → importuj to isté GitHub repo.
2. **Root Directory**: `frontend` (Settings → General → Root Directory).
3. Environment variables (Settings → Environment Variables):
   - `NEXT_PUBLIC_API_URL` = `https://<render-url>` (bez lomky)
   - `NEXT_PUBLIC_WS_URL` = `wss://<render-url>/ws/live`
4. **Deploy**. Hotovo — otvor si link v telefóne.

## Krok 4 — Dokoľky (CORS)

V Render dashboarde → `surebet-api` → Environment: nahraď `CORS_ORIGINS`
hodnotu `*` skutočnou URL Vercel frontendu, potom **Manual Deploy → Deploy
latest commit** (alebo len Save, Render redeployne automaticky pri zmene env).

## Časté problémy

- **Frontend hlási „Backend unreachable"** — zlá `NEXT_PUBLIC_API_URL` (musí
  byť `https://`, bez lomky na konci; WS cez `wss://`).
- **401 na WS / prázdny feed** — Render free plan zaspal; obnov stránku.
- **Pomalý prvý načítanie API** — demo seed beží pri štarte, niekoľko desiatok
  sekúnd je normálnych.
- **Vidím len DEMO MODE badge** — to je správne, celá platforma funguje výhradne
  na simulovaných dátach.
