# jersa_test_framework — Project Guide

## Co budujemy

Framework do automatyzacji testów w Pythonie dla sklepu **jersa-storefront** (`ironz1/jersa-storefront`). Projekt portfolio pod role SDET (Python, Playwright, API, GitHub Actions, AWS) oraz nauka całego procesu tworzenia i utrzymania frameworka.

Pełne założenia, etapy, ryzyka i decyzje: **`KNOWLEDGE.md`**.

## System testowany

| Warstwa | Opis |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind 4 |
| API | BFF w Route Handlers: `/api/commerce/*`, `/api/admin/*` (po zalogowaniu, ciasteczko). Brak OpenAPI |
| Baza | Prisma 6 — SQLite lokalnie, Neon Postgres na Vercelu; w testach Postgres (Docker) |
| Hosting | Vercel Hobby; PayU na mocku |

Sklep jest w osobnym repo — na tym etapie nie zmieniamy jego architektury.

## Stack frameworka

Python 3.12 (uv, `pyproject.toml` + `uv.lock`), pytest, Playwright (pytest-playwright), requests, psycopg 3, jsonschema, pydantic-settings, ruff; pytest-xdist od Etapu 4, narzędzie raportów w Etapie 5. CI: **tylko GitHub Actions** (bez Azure DevOps i GitLab CI). AWS dopiero w Etapie 6.

## Docelowa struktura

```
tests/{contract,api,db,e2e}/   # testy wg poziomu
tests/framework/               # testy samego frameworka (bez sklepu, w CI)
schemas/                       # schematy JSON per endpoint
src/jersa/{clients,pages,db,schemas,fixtures}/  # klient HTTP, page objecty, SQL, loader schematów, fixtures
src/jersa/clients/commerce.py  # CommerceApi: jedna metoda na endpoint sklepu (fixtures shop, make_shop)
src/jersa/db/{products,orders}.py  # własny produkt testu, odczyt zamówień
src/jersa/traceability.py  scripts/build_traceability.py  docs/traceability.json  # macierz śledzenia
src/jersa/config.py            # Settings (pydantic-settings) z .env
conftest.py  pyproject.toml  uv.lock  .env.example  docker-compose.yml  .github/workflows/ci.yml
```

## Konwencje

- Markery pytesta przecinają poziomy testów: każdy test sklepu ma `regression`, ścieżka krytyczna dodatkowo `smoke`, kontrakt dodatkowo `contract`.
- Piramida: im wyższy poziom (E2E), tym mniej scenariuszy.
- Dane testowe: unikalny prefiks uuid w danych każdego testu; teardown usuwa **tylko własne rekordy po ID**. Nigdy nie czyścimy całych tabel.
- Własny produkt na test (ADR-012): test, który coś kupuje albo dodaje opinię, bierze produkt z fixture `product` / `make_product(...)` (`test-<hex>`), nigdy produkt z seeda. Seed jest tylko czytany. Asercje stanu magazynowego porównują ze stanem sprzed akcji, bez liczb seeda na sztywno (ADR-013).
- Testy zachowań, które sklep ma dopiero poprawić, nie trafiają do publicznego repo przed poprawką (ADR-014); `xfail` z opisem słabości też nie.
- Schematy kontraktów: `additionalProperties: false`, spisywane z realnych odpowiedzi.
- Testy muszą być niezależne i działać równolegle (pytest-xdist).
- Sekrety tylko w `.env` (nie commitujemy); wzór w `.env.example`. Repo jest **publiczne**.
- Zero stanu globalnego: dane między testami tylko przez fixtures. Fixtures w `src/jersa/fixtures/`, rejestrowane w `pytest_plugins` głównego `conftest.py`.
- Adresy w `.env` przez `127.0.0.1`, nie `localhost` (na Windows `localhost` → najpierw `::1`, a porty compose są tylko na IPv4).
- Macierz śledzenia: każdy test sklepu ma wpis w `docs/traceability.json` (przypadek → wymaganie → funkcja testu), a jego docstring zaczyna się od ID przypadku. Po zmianie danych: `uv run python scripts/build_traceability.py` i commit PDF razem z JSON-em. Pełna instrukcja: `KNOWLEDGE.md` sekcja 7.
- Równoległość: `uv run pytest` idzie domyślnie na 4 procesach (`-n 4` w `addopts`, ADR-015). Do debugowania i podglądu `--headed` używaj `-n 0`.
- Polecenia: `uv run pytest -m smoke`, `uv run pytest tests/framework -n 0`, `uv run ruff check`, `uv run ruff format`.

## Sposób pracy

- Cel nauki jest równie ważny jak kod: przy decyzjach tłumacz *dlaczego* i pokazuj alternatywy.
- Każdą istotną decyzję zapisuj w `KNOWLEDGE.md` jako ADR (sekcja 4); pole „Na rozmowie” też uzupełniaj (dotyczy też wpisów w sekcji 6): 1–3 proste zdania, które da się powiedzieć na głos na rozmowie rekrutacyjnej, bez lania wody i bez żargonu, którego nie trzeba.
- Problemy rozwiązane w trakcie → `KNOWLEDGE.md` sekcja 6; postęp etapów → sekcja 2.
- Po drodze dopisuj pytania rekrutacyjne z odpowiedziami do `KNOWLEDGE.md` sekcja 9 (krótko, z dowodem w projekcie). Priorytet mają tematy najbliższej rozmowy: bazy danych, quality gate, CI/CD, Python.
- Po każdym istotnym kroku dopisz go do `KNOWLEDGE.md` sekcja 8 (numerowana lista, jedno zdanie: co i po co).

## Status projektu

**Aktualny etap:** Etap 5 — CI. Równolegle kasa sklepu: krok 1 zrobiony i scalony 2026-11-19 w parze z `feat/payu` sklepu (dopasowanie 6 testów, A-CART-14, R25–R26; 154 testy, bramka zielona); krok 2 (nowe testy kasy, kodów rabatowych, PayU z kwotą, panelu kodów) w toku na gałęzi `kasa-krok-2`. 5A zrobione 2026-11-17: bramka testów na PR sklepu (workflow `tests` w repo sklepu, ADR-016), informacyjna, bo reguła ochrony nie jest egzekwowana w prywatnym repo na darmowym planie; zostaje 5B (job w repo testów, nightly, smoke po deployu, raporty, egzekwowanie na wdrożeniu). Etap 4 — równoległość (`-n 4`) zrobiony 2026-11-16. Etap 3, krok A zrobiony 2026-11-13 (83 testy sklepu + 65 frameworka, macierz śledzenia; po Etapie 4 frameworka jest 67); krok B (kolejne testy API) czeka na zmianę w sklepie. Etap 2 zamknięty 2026-11-06; repo publiczne <https://github.com/ironz1/jersa_test_framework>. Sklep w Dockerze: `docker compose up -d --build --wait` (`127.0.0.1:3100`).
