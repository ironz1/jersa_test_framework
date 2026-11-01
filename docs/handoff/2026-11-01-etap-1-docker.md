# Zadanie dla repo jersa-storefront: obraz Docker sklepu

- **Od:** repo testów `jersa_test_framework` (katalog repo)
- **Data:** 2026-11-01
- **Pełny projekt:** `docs\superpowers\specs\2026-11-01-etap-1-docker-design.md`

## Kontekst

Osobne repo `jersa_test_framework` (Python: pytest, Playwright, requests, psycopg) testuje ten sklep przez HTTP, przeglądarkę i bazę. Testy potrzebują sklepu uruchamianego w Dockerze z Postgresem — lokalnie i w GitHub Actions. `docker-compose.yml` jest w repo testów; **obraz sklepu (Dockerfile) jest w tym repo**, bo zmienia się razem z kodem.

Compose repo testów uruchamia:
1. `postgres:16`,
2. `db-init` — etap `builder` tego Dockerfile, polecenie `node scripts/prepare-database.mjs` z `COMMERCE=own` i `DATABASE_URL=postgresql://jersa:jersa@postgres:5432/jersa` (generate + `db push` + seed), kończy się,
3. `app` — etap `runner`, `node server.js` na porcie 3000.

## Zadanie

Nie zmieniaj logiki aplikacji, UI ani API. Commit lokalny, **bez pusha** (push zleci człowiek).

1. `next.config.ts`: dodaj `output: "standalone"`.
2. `scripts/prepare-database.mjs`: dodaj tryb `--generate-only` — zapisuje `prisma/schema.postgres.prisma` i uruchamia `prisma generate` dla niego, **bez** `db push` i seeda i bez potrzeby działającej bazy. Domyślne zachowanie (używane przez `npm run build` na Vercelu) bez zmian.
3. `Dockerfile` (multi-stage, `node:22-bookworm-slim`):
   - `deps`: `npm ci`.
   - `builder`: źródła; `node scripts/prepare-database.mjs --generate-only`; `next build` (nie przez `npm run build`, żeby nie łączyć się z bazą).
   - `runner`: `.next/standalone` + `.next/static` → `.next/static` + `public/` → `public/`; `NODE_ENV=production`, `HOSTNAME=0.0.0.0`, `PORT=3000`; użytkownik nie-root; `CMD ["node", "server.js"]`.
4. `.dockerignore`: `node_modules`, `.next`, `.env*`, `prisma/**/*.db`, `.git`, `test-results`, `playwright-report`.

### Pułapki — sprawdź świadomie

- **Prisma Client pod Postgres.** Bez kroku `--generate-only` w obrazie zostanie klient SQLite (postinstall `@prisma/client`) i sklep padnie przy pierwszym zapytaniu.
- **Standalone nie kopiuje `public/` ani `.next/static`** — bez nich brak zdjęć, CSS i JS.
- **`HOSTNAME=0.0.0.0`** — inaczej serwer nie odpowiada z hosta.
- **Prerender w `next build`.** Jeśli build prerenderuje strony czytające bazę, w Dockerze (bez bazy) się wywali. **Najpierw sprawdź i opisz**, co się dzieje. Rozwiązanie bez zmian w aplikacji (np. baza dostępna w buildzie) wybierz sam; rozwiązanie zmieniające zachowanie aplikacji (np. wymuszenie renderowania w runtime) — tylko po zgodzie człowieka.

## Kryteria akceptacji

- `docker build --target runner .` przechodzi.
- `npx tsc --noEmit` i `npx vitest run` zielone.
- `npm run build` z URL Postgres działa jak dotąd.
- Lista zmiennych środowiskowych potrzebnych sklepowi w runtime (np. hasło `/admin`) — wypisz w podsumowaniu.

## Stałe zasady — dopisz do `CLAUDE.md` (Hard rules / Decision log) i `docs/PLAN.md`

- Repo `jersa_test_framework` testuje `/api/commerce/*` testami kontraktu (JSON Schema, `additionalProperties: false`). Dodanie, usunięcie lub zmiana typu pola w odpowiedzi łamie te testy — opisz taką zmianę w commicie.
- `Dockerfile`, `.dockerignore`, `output: "standalone"` i tryb `--generate-only` są częścią projektu: nie usuwaj; aktualizuj Dockerfile przy zmianie zależności, wersji Node, sposobu budowania lub nowych katalogów potrzebnych w runtime.
- Zmiana schematu Prismy (tabele, kolumny) wpływa na testy DB w `jersa_test_framework` — opisz ją w commicie.

## Po zakończeniu

Podsumuj: zmienione pliki, wynik kryteriów, co zrobiłeś z prerenderem, lista zmiennych runtime.
