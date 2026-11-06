# jersa_test_framework

Framework do automatyzacji testów w Pythonie dla sklepu internetowego **jersa-storefront** (Next.js, API BFF, Postgres). Projekt portfolio pod rolę SDET: testy kontraktu, API, bazy danych i E2E, środowisko w Dockerze, CI w GitHub Actions.

Decyzje projektowe (ADR), etapy i notatki: [`KNOWLEDGE.md`](KNOWLEDGE.md). Mapa środowiska testowego: [`docs/mapa-srodowiska.pdf`](docs/mapa-srodowiska.pdf).

## Stack

Python 3.12 (uv), pytest, Playwright, requests, psycopg 3, jsonschema, pydantic-settings, ruff, GitHub Actions.

## Uruchomienie

Wymagania: [uv](https://docs.astral.sh/uv/), Docker, lokalny klon sklepu (ścieżka w `STOREFRONT_PATH`).

```bash
cp .env.example .env                    # uzupełnij STOREFRONT_PATH
docker compose up -d --build --wait     # sklep na 127.0.0.1:3100, Postgres na 127.0.0.1:5432
uv sync
uv run playwright install chromium
uv run pytest -m smoke                  # po jednym teście na każdym poziomie
uv run pytest tests/framework           # testy samego frameworka, bez sklepu
```

Testy na STG: `BASE_URL=https://jersa-storefront.vercel.app uv run pytest tests/contract` (bez `DATABASE_URL` testy bazy są pomijane).

## Struktura

```
src/jersa/            kod frameworka
  config.py           konfiguracja z .env (pydantic-settings)
  clients/            klient HTTP do API sklepu
  db/                 połączenie z Postgresem
  schemas/            loader schematów JSON
  pages/              page objecty Playwright
  fixtures/           fixtures pytest (ładowane w conftest.py)
schemas/              schematy kontraktów API (JSON Schema 2020-12)
tests/
  contract/ api/ db/ e2e/   testy wg poziomu
  framework/                testy frameworka (uruchamiane w CI)
docker-compose.yml    sklep + Postgres + seed (DEV)
```

Markery: `smoke`, `regression`, `contract`.
