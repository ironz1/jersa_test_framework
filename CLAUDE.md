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

Python, pytest, Playwright (pytest-playwright), requests, psycopg2, jsonschema, pytest-html, pytest-xdist, ruff. CI: **tylko GitHub Actions** (bez Azure DevOps i GitLab CI). AWS dopiero w Etapie 6.

## Docelowa struktura

```
tests/{contract,api,db,e2e}/   # testy wg poziomu
schemas/                       # schematy JSON per endpoint
src/{clients,pages,db,schemas}/  # klient HTTP, page objecty, SQL, loader schematów
conftest.py  pytest.ini  requirements.txt  .env.example  docker-compose.yml
```

## Konwencje

- Markery pytesta: `smoke`, `regression`, `contract` — przecinają poziomy testów.
- Piramida: im wyższy poziom (E2E), tym mniej scenariuszy.
- Dane testowe: unikalny prefiks uuid w danych każdego testu; teardown usuwa **tylko własne rekordy po ID**. Nigdy nie czyścimy całych tabel.
- Schematy kontraktów: `additionalProperties: false`, spisywane z realnych odpowiedzi.
- Testy muszą być niezależne i działać równolegle (pytest-xdist).
- Sekrety tylko w `.env` (nie commitujemy); wzór w `.env.example`.

## Sposób pracy

- Cel nauki jest równie ważny jak kod: przy decyzjach tłumacz *dlaczego* i pokazuj alternatywy.
- Każdą istotną decyzję zapisuj w `KNOWLEDGE.md` jako ADR (sekcja 4); pole „Na rozmowie” zostawiaj do uzupełnienia użytkownikowi.
- Problemy rozwiązane w trakcie → `KNOWLEDGE.md` sekcja 6; postęp etapów → sekcja 2.
- Po każdym istotnym kroku dopisz go do `KNOWLEDGE.md` sekcja 8 (numerowana lista, jedno zdanie: co i po co).

## Status projektu

**Aktualny etap:** Etap 1 — sklep w Dockerze: działa lokalnie (`docker compose up -d --build --wait`); do zamknięcia push sklepu i zielony deploy na Vercelu.
