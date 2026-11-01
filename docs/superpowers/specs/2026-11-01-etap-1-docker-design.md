# Etap 1 — sklep w Dockerze (projekt)

- **Data:** 2026-11-01
- **Status:** zatwierdzony w rozmowie, do planu
- **Powiązane:** `KNOWLEDGE.md` ADR-003, ADR-005, ADR-006; notka dla Groka: `docs/handoff/2026-11-01-etap-1-docker.md`

## Po co

Testy (API, DB, E2E) potrzebują sklepu, który da się postawić jedną komendą, zawsze w tym samym stanie (czysty Postgres + seed), lokalnie i na runnerze GitHub Actions. Docker pełni rolę DEV (laptop) i INT (CI); `jersa-storefront.vercel.app` to STG.

Dziś sklep lokalnie działa na SQLite, a na Vercelu na Neon Postgres — Docker z Postgresem to pierwsze miejsce przed STG z tą samą bazą co na Vercelu.

## Cele

- `docker compose up --build --wait` stawia Postgres, przygotowuje bazę (schemat + seed) i uruchamia sklep na `http://localhost:3000`.
- Postgres dostępny dla testów DB na `localhost:5432`.
- `docker compose down -v` + ponowny `up` = świeża baza.
- Ten sam compose działa lokalnie (Windows + Docker Desktop/WSL2) i na runnerze Ubuntu.

## Non-goals

- Uruchamianie frameworka testowego w kontenerze (otwarta decyzja, najpóźniej Etap 6).
- Publikacja obrazu w GHCR/ECR (Etap 5/6).
- Workflow CI (Etap 5).
- Zmiany logiki sklepu, UI, API.

## Anti-goals (porażka, nawet jeśli „działa”)

- Zmiana zachowania deployu na Vercelu.
- Obraz z Prisma Client pod SQLite (sklep wstaje, ale pada przy pierwszym zapytaniu).
- Sklep w kontenerze bez zdjęć/CSS (brak `public/` lub `.next/static`).
- Sekrety lub lokalna baza SQLite w obrazie.

## Ograniczenia

- Zmiany w repo sklepu wprowadza **Grok** (agent w `jersa-storefront`) według notki; commit lokalny, push zleca człowiek. Ja (agent repo testów) nie edytuję repo sklepu.
- Commitowany `prisma/schema.prisma` ma provider `sqlite`; Postgres przez `scripts/prepare-database.mjs` (rewrite do gitignore'owanego `prisma/schema.postgres.prisma`).
- `npm run build` = `prepare-database.mjs && next build`; na Vercelu `prepare-database` robi generate + `db push` + seed w czasie builda. W `docker build` bazy nie ma.
- `prisma` i `tsx` są w `devDependencies` — nie trafią do obrazu standalone.
- Brak migracji — tylko `db push`.
- Lokalny klon sklepu: `%USERPROFILE%\Documents\Repos\jersa-storefront`.

## Decyzje (z rozmowy)

1. **Dockerfile w repo sklepu, `docker-compose.yml` w repo testów** (ADR-006). Repo aplikacji produkuje obraz, repo testów go konsumuje.
2. **Przygotowanie bazy w osobnej usłudze `db-init`**, nie w entrypoincie aplikacji — narzędzia (Prisma CLI, tsx) zostają poza obrazem runtime, brak skryptu shell (ryzyko CRLF).
3. **Izolacja testów na poziomie testu** (ADR-003): Docker daje świeżą bazę per przebieg; na STG testy tworzą własne dane (np. własny `ProductRow` ze `stockBySize`) i sprzątają po ID.

## Zmiany w repo sklepu (Grok)

| # | Plik | Zmiana |
|---|---|---|
| 1 | `next.config.ts` | `output: "standalone"` |
| 2 | `scripts/prepare-database.mjs` | tryb `--generate-only`: zapis `schema.postgres.prisma` + `prisma generate`, **bez** `db push` i seeda, bez wymogu działającej bazy (wymaga tylko ustawienia trybu Postgres, np. flagą lub zmienną). Domyślne zachowanie (Vercel) bez zmian |
| 3 | `Dockerfile` | multi-stage, opis niżej |
| 4 | `.dockerignore` | `node_modules`, `.next`, `.env*`, `prisma/**/*.db`, `.git`, `test-results`, `playwright-report` |
| 5 | `CLAUDE.md` + `docs/PLAN.md` | wpis do Decision log + stałe zasady (sekcja „Stałe zasady” w notce) |

### Dockerfile

| Etap | Bazuje na | Robi |
|---|---|---|
| `deps` | `node:22-bookworm-slim` | `npm ci` (pełne zależności, także dev) |
| `builder` | `deps` | kopiuje źródła; `prepare-database --generate-only` (klient Prismy pod Postgres); `next build` (bez `prepare-database` w pełnym trybie) |
| `runner` | `node:22-bookworm-slim` | kopiuje `.next/standalone`, `.next/static` → `.next/static`, `public/` → `public/`; `NODE_ENV=production`, `HOSTNAME=0.0.0.0`, `PORT=3000`; użytkownik nie-root; `CMD ["node", "server.js"]` |

Etap `builder` służy też jako obraz dla `db-init` (`target: builder`).

**Moje decyzje (do sprawdzenia przez człowieka):**
- Node 22 LTS, Debian slim (nie Alpine) — `builder` i `runner` na tym samym systemie, więc silnik Prismy wygenerowany jako `native` pasuje do runtime bez zmiany `binaryTargets`.
- `HOSTNAME=0.0.0.0` — bez tego `server.js` standalone nasłuchuje tylko wewnątrz kontenera i port 3000 z hosta nie odpowiada.

### Znane ryzyko: prerender w `next build`

Jeśli `next build` prerenderuje strony katalogu (RSC, ISR) i czyta przy tym bazę, build w Dockerze bez bazy się nie powiedzie (na Vercelu baza jest dostępna w buildzie). Grok ma to sprawdzić **przed** wyborem rozwiązania i zgłosić, jeśli rozwiązanie zmienia zachowanie aplikacji:
- (a) build z dostępem do Postgresa (np. tymczasowa baza w buildzie) — bez zmian w aplikacji, ale cięższy build;
- (b) wymuszenie renderowania w runtime dla stron czytających bazę — zmiana w aplikacji, wymaga zgody człowieka;
- (c) inne rozwiązanie Groka — opisane przed wdrożeniem.

## `docker-compose.yml` (repo testów, ja)

| Usługa | Obraz / build | Konfiguracja | Gotowość |
|---|---|---|---|
| `postgres` | `postgres:16` | `jersa/jersa/jersa`, port `5432:5432`, wolumen nazwany | healthcheck `pg_isready` |
| `db-init` | build sklepu, `target: builder` | `COMMERCE=own`, `DATABASE_URL=postgresql://jersa:jersa@postgres:5432/jersa`; `node scripts/prepare-database.mjs`; kończy się | `depends_on: postgres: service_healthy` |
| `app` | build sklepu, `target: runner` | te same zmienne, port `3000:3000` | `depends_on: db-init: service_completed_successfully`; healthcheck `node -e "fetch('http://localhost:3000/api/commerce/search?q=castello')…"` sprawdza, że w odpowiedzi jest `zakiet-castello` (obraz slim nie ma `curl`) |

- Kontekst builda: zmienna `STOREFRONT_PATH` (domyślnie `../../Documents/Repos/jersa-storefront` względem repo testów lokalnie; w CI ścieżka checkoutu). Wzór w `.env.example`.
- Zmienne runtime sklepu (np. hasło `/admin`) — lista od Groka, trafiają do `.env.example` repo testów.

## Kryteria akceptacji

**Repo sklepu (Grok, przed commitem):**
- `docker build --target runner .` przechodzi.
- `npx vitest run` zielony, `npx tsc --noEmit` bez błędów.
- `npm run build` lokalnie zachowuje się jak dotąd (pełny `prepare-database` przy URL Postgres).

**Całość (ja, po pushu sklepu):**
- `docker compose up --build --wait` kończy się sukcesem.
- `GET http://localhost:3000/api/commerce/search?q=castello` → produkt `zakiet-castello`.
- Strona główna i PDP CASTELLO renderują się ze zdjęciami.
- `psql`/psycopg na `localhost:5432` widzi tabelę `ProductRow` z 5 produktami.
- `down -v` + `up` → seed od nowa (5 szt. na rozmiar).
- Deploy na Vercelu po pushu zielony.

## Zostawione wykonawcy

- Dokładna implementacja `--generate-only` (flaga CLI vs zmienna).
- Kolejność warstw i cache w Dockerfile.
- Wybór rozwiązania ryzyka prerendera w granicach opisanych wyżej.
