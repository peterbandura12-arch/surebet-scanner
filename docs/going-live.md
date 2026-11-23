# Pripojenie reálnych dát (The Odds API) — návod po kročkoch

Tento návod je písaný obyčajnou rečou. Predpokladám, že aplikácia už beží na
Rendri (backend) a Verceli (frontend) podľa `docs/deploy.md`.

Dovtedy (alebo kým nezadáš kľúč) beží aplikácia čisto na **demo dátach** —
každá obrazovka to jasne označuje (`DEMO MODE`, `simulated`). Nič na tom
nezmeníš klikaním — potrebný je jeden **reálny API kľúč**.

---

## 1. Čo potrebuješ

- Účet na Renderi (už máš).
- Zadarmo vytvorený kľúč od **The Odds API** — to je legitímna platená/free
  služba, ktorá predáva športové kurzy cez oficiálne API. My neskrabujeme
  weby, nepodvádzame žiadne limity, ani si nevymýšľame kľúče.

## 2. Ako si zadarmo založím kľúč (5 minút)

1. Na telefóne alebo PC otvor **https://the-odds-api.com/**
2. Klikni na **„Get API Key"** (alebo *Sign up*).
3. Zadaj e-mail a heslo → potvrdíš registráciu.
4. Po prihlásení ti na stránke (a mailom) zobrazí **API key** — dlhý kód
   niečo ako `a1b2c3d4e5f6...`. Ten si **skopíruj** do poznámok.
5. Free plán ti dá **500 kreditov mesačne**. 1 kredit = 1 požiadavka na
   kurzy pre 1 šport a 1 trh. Aplikácia je nastavená tak, aby šetrila:
   defaultne ťahá dáta maximálne každých **60 sekúnd** (meniteľné).

> ⚠️ Kľúč je tajomstvo, ako heslo. Nikdy ho nevkladaj na verejné miesto,
> nedávaj ho do frontendu a neposielaj nikomu. Vkladať ho budeš **len**
> do Renderu do environment variables — tam je bezpečne.

## 3. Kam kľúč vložím (iba Render, pár klikov)

1. Otvor **dashboard.render.com** → klikni na službu **surebet-api**.
2. Vľavo vyber záložku **Environment**.
3. Klikni **Add environment variable** a pridaj:

   | Name                 | Value                          |
   |----------------------|--------------------------------|
   | `THEODDSAPI_KEY`     | tvoj skopírovaný API key       |

4. (Voliteľné — môžeš ponechať prednastavené z render.yaml):

   | Name                          | Príklad hodnoty                              | K čomu je |
   |-------------------------------|----------------------------------------------|-----------|
   | `THEODDSAPI_REGION`           | `eu`                                         | región bookmakerov (eu/us/uk/au) |
   | `THEODDSAPI_SPORTS`           | `soccer_epl,basketball_nba,icehockey_nhl`    | ktoré športy sledovať — každý extra šport žerie viac kreditov! |
   | `THEODDSAPI_MARKETS`          | `h2h` alebo `h2h,spreads,totals`             | viac trhov = viac kreditov |
   | `THEODDSAPI_MIN_INTERVAL_SECONDS` | `60`                                     | ochrana kreditov (min. interval ťahania) |

5. Klikni **Save changes** — Render automaticky reštartuje backend
   (alebo daj manuálne *Manual Deploy → Deploy latest commit*).

## 4. Ako si overím, že reálne dáta tečú

Počkaj ~1–2 minúty po reštarte, potom:

1. Otvor v aplikácii stránku **Data Sources**.
   - Mal by byť vidieť zdroj **The Odds API** so stavom `active`,
     s čerstvým `last_sync_at` a prázdnym `last_error`.
   - Ak je tam `last_error` typu `invalid_api_key` → skontroluj, či sa
     kľúč skopíroval celý. `rate_limited` → kľúč je OK, len minul kvótu.
2. Otvor **Live Scanner**.
   - Pri položkách z reálneho zdroja uvidíš značky ako `toa_*` (The Odds API
     bookmakeri) namiesto `demo_*`.
   - Eventy z reálneho zdroja **nie sú** označené ako simulated.
   - Eventy z demo zdroja stále zobrazujú DEMO / simulated — to je správne.
3. Core API kontrola (voliteľne): `https://tvoje-api.onrender.com/api/sources`.

## 5. Koľko kreditov to spotrebuje (aby ťa to nezaskočilo)

Free plán = **500 kreditov / mesiac**. Spotreba:

- 1 šport × 1 trh (`h2h`) × ťahanie každých 60 s ≈ **43 200 žiadostí /
  mesiac** → to by free plán vyčerpal za pár hodín.

Preto odporúčam pre začiatok:

- `THEODDSAPI_MIN_INTERVAL_SECONDS=600` (každých 10 minút) a
- `THEODDSAPI_SPORTS=soccer_epl` (len jeden šport) a
- `THEODDSAPI_MARKETS=h2h` (len základný trh).

Týchto 500 kreditov ti potom vystačí približne na 80+ hodín reálneho
scanovania mesačne — napríklad 2–3 hodiny denne. Ak chceš viac, The Odds API
má platené plány.

API odpovedá hlavičkami `x-requests-remaining` / `x-requests-used`, aplikácia
si ich zaznamenáva a pri 429 (kvóta) prejde do stavu `rate_limited` a čaká.
Demo dáta **nikdy nenahrádzajú** to, čo reálny zdroj nedodal — nijako sa
nezamieňajú.

## 6. Dôležité upozornenia

- **Žiadne reálne stávky.** Aplikácia nezadáva tipy, neposielá peniaze,
  nič neplatí. Paper trading = len virtuálne peniaze na virtuálnom účte.
- **Surebety z reálnych kurzov sú teoretické.** V praxi medzi kurzom a
  tvojou objednávkou kurz často stihne zmeniť, niektoré bookmakre majú
  limity, poplatky, oneskorenia. Považuj výsledok za **analytický odhad**,
  nie garantovaný zisk.
- **Nie je to investičné poradenstvo.** Iba nástroj na matematickú
  arbitrážnu analýzu.
- Kľúč nikdy nezdieľaj ani nunca nevkladaj do frontendu — je to tajomstvo.

---

## Troubleshooting

| Symptom | Príčina | Riešenie |
|---|---|---|
| `Data Sources` → `inactive`, no key | `THEODDSAPI_KEY` nie je nastavený | Doplniť v Render → Environment |
| `invalid_api_key` | nesprávny/nekopírovaný kľúč | Skopírovať znovu z the-odds-api.com |
| `unknown_sport` | zlý kód športu v `THEODDSAPI_SPORTS` | Skontrolovať kódy na the-odds-api.com |
| `rate_limited` | minula sa kvóta/nízky interval | Zvýšiť `THEODDSAPI_MIN_INTERVAL_SECONDS` alebo čakať do ďalšieho mesačného resetu |
| Nič sa nezmenilo | Render sa nereštartoval | Manual Deploy → Deploy latest commit |
