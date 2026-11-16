# jersa_test_framework

Framework do automatyzacji testów w Pythonie dla sklepu internetowego **jersa-storefront** (Next.js, API BFF, Postgres). Projekt portfolio pod rolę SDET: testy kontraktu, API, bazy danych i E2E, środowisko w Dockerze, CI w GitHub Actions.

- Decyzje projektowe (ADR), etapy i notatki: [`KNOWLEDGE.md`](KNOWLEDGE.md)
- Które wymaganie sprawdza który test: [`docs/traceability-matrix.pdf`](docs/traceability-matrix.pdf)
- Mapa środowiska testowego: [`docs/mapa-srodowiska.pdf`](docs/mapa-srodowiska.pdf)
- Komendy do uruchamiania testów: [`docs/komendy.md`](docs/komendy.md)

## Stack

Python 3.12 (uv), pytest, Playwright, requests, psycopg 3, jsonschema, pydantic-settings, ruff, GitHub Actions.

## Testy

| Poziom | Liczba | Co sprawdza |
|---|---|---|
| Kontrakt | 10 | kształt odpowiedzi API względem schematów JSON |
| API | 51 | reguły koszyka, zamówienia, płatności, opinii, przechowalni i wyszukiwarki |
| Baza | 17 | czy skutek akcji z API naprawdę jest w Postgresie |
| E2E | 5 | kluczowe ścieżki klienta w przeglądarce |
| Framework | 65 | sam framework, bez sklepu (uruchamiane w CI) |

Testy, które coś kupują albo dodają opinię, dostają z fixture własny produkt (`test-<hex>`) i usuwają go po sobie. Dane startowe sklepu są tylko czytane.

## Uruchomienie

Wymagania: [uv](https://docs.astral.sh/uv/), Docker, lokalny klon sklepu (ścieżka w `STOREFRONT_PATH`).

```bash
cp .env.example .env                    # uzupełnij STOREFRONT_PATH
docker compose up -d --build --wait     # sklep na 127.0.0.1:3100, Postgres na 127.0.0.1:5432
uv sync
uv run playwright install chromium
uv run pytest                           # wszystko: ok. 12 s
uv run pytest -m smoke                  # ścieżka krytyczna na każdym poziomie
uv run pytest -m regression             # wszystkie testy sklepu
uv run pytest tests/api                 # jeden poziom: contract, api, db albo e2e
uv run pytest tests/framework           # testy samego frameworka, bez sklepu
```

Testy na STG (bash): `BASE_URL=https://jersa-storefront.vercel.app DATABASE_URL= uv run pytest tests/contract tests/api`. Pusty `DATABASE_URL` jest konieczny: testy z własnym produktem i testy bazy są wtedy pomijane, zamiast wstawiać dane do lokalnej bazy i pytać o nie STG.

## Struktura

```
src/jersa/            kod frameworka
  config.py           konfiguracja z .env (pydantic-settings)
  clients/            klient HTTP i operacje klienta sklepu (jedna metoda na endpoint)
  db/                 połączenie z Postgresem, własny produkt testu, odczyt zamówień
  schemas/            loader schematów JSON
  pages/              page objecty Playwright
  fixtures/           fixtures pytest (ładowane w conftest.py)
  traceability.py     macierz śledzenia wymagań: sprawdzanie danych i HTML
schemas/              schematy kontraktów API (JSON Schema 2020-12)
tests/
  contract/ api/ db/ e2e/   testy wg poziomu
  framework/                testy frameworka (uruchamiane w CI)
docs/traceability.json      wymagania i przypadki testowe (źródło macierzy)
scripts/              budowanie PDF macierzy
docker-compose.yml    sklep + Postgres + seed (DEV)
```

Markery: `regression` (każdy test sklepu), `smoke` (ścieżka krytyczna), `contract` (testy kontraktu).

Nowy test: kod w `tests/<poziom>/`, wpis w `docs/traceability.json`, potem `uv run python scripts/build_traceability.py`. Szczegóły: [`KNOWLEDGE.md`](KNOWLEDGE.md), sekcja 7.
