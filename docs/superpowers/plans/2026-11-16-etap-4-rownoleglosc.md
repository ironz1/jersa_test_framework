# Etap 4 — Równoległość (pytest-xdist) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `uv run pytest` uruchamia domyślnie 4 procesy (w tym E2E), a wszystkie testy przechodzą powtarzalnie i nie zostawiają śladów w bazie.

**Architecture:** `pytest-xdist` w grupie `dev`, `-n 4` w `addopts`. Przyczyny kolizji (jeśli wystąpią) naprawiamy przez własne dane testu, nie przez serializację. Dowód: 3 przebiegi z rzędu na `-n 4` i kontrola stanu bazy.

**Tech Stack:** Python 3.12, uv, pytest 9, pytest-xdist, Playwright, Postgres w Dockerze (`127.0.0.1:5432`), sklep `127.0.0.1:3100`.

**Spec:** `docs/superpowers/specs/2026-11-16-etap-4-rownoleglosc-design.md`

## Global Constraints

- `-n 4` w `addopts` w `pyproject.toml`; `-n 0` wyłącza równoległość (debugowanie, `--pdb`, `HEADED=true`).
- `pytest-xdist` w grupie `dev` (`uv add --dev pytest-xdist`), `uv.lock` commitowany.
- Dystrybucja domyślna (`load`); `loadfile` i marker `serial` tylko po zapisanym uzasadnieniu (ADR).
- Teardown usuwa tylko własne rekordy po ID; nigdy nie czyścimy całych tabel (CLAUDE.md).
- Adresy w `.env` przez `127.0.0.1`. Repo jest publiczne: brak sekretów, plików lokalnych (`docs/scenariusze-etap-3.md`, `docs/handoff/*`) nie commitujemy.
- Polecenia kontrolne: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`.
- Praca na gałęzi `etap-4-rownoleglosc` (bramka wymaga PR; push i merge dopiero po zgodzie właściciela).

## Review Focus

1. Testy czytające globalne dane (wyszukiwanie „castello”, listy produktów): równoległe wstawianie produktów `test-*` nie może zmieniać wyniku asercji.
2. `HEADED=true` w `.env` przy `-n 4`: 4 okna; `--pdb` z `-n`: błąd. Oba przypadki opisane z `-n 0`.
3. Limit połączeń Postgres (domyślnie 100): 4 procesy × połączenia `db` i sprzątania muszą się mieścić, a połączenia zamykać.
4. Zwolniony start: `tests/framework` w CI na 4 procesach nie może być wolniejszy niż jednoprocesowo; jeśli jest, `-n 0` w `ci.yml`.
5. Ślady po przebiegu: koszyki, przechowalnie, zamówienia, produkty `test-*` = 0 i seed bez zmian po każdym z 3 przebiegów.

---

### Task 1: xdist w konfiguracji (z testem pilnującym)

**Files:**
- Create: `tests/framework/test_pytest_config.py`
- Modify: `pyproject.toml` (grupa `dev`, `addopts`), `uv.lock`

**Interfaces:**
- Produces: `addopts` w `[tool.pytest.ini_options]` zawiera `-n 4`; pakiet `xdist` importowalny.

- [ ] **Step 1: Punkt odniesienia.** Sklep działa (`docker compose up -d --build --wait`). Uruchom `uv run pytest` i zapisz czas oraz liczbę testów (oczekiwane: 148 passed). Zapisz też czas `uv run pytest tests/framework`.
- [ ] **Step 2: Napisz test `test_xdist_is_installed` i `test_default_run_uses_four_workers`** w `tests/framework/test_pytest_config.py`. Pierwszy: `importlib.util.find_spec("xdist")` nie jest `None`. Drugi: `tomllib` wczytuje `pyproject.toml` (ścieżka względem pliku testu: `Path(__file__).parents[2]`) i `"-n 4"` występuje w `tool.pytest.ini_options.addopts`.
- [ ] **Step 3: Uruchom `uv run pytest tests/framework/test_pytest_config.py`.** Expected: oba FAIL (brak xdist, brak `-n 4`).
- [ ] **Step 4: `uv add --dev pytest-xdist`, potem w `addopts` dopisz `-n 4`** (wynik: `"--strict-markers -ra -n 4"`).
- [ ] **Step 5: Uruchom `uv run pytest tests/framework/test_pytest_config.py -n 0`.** Expected: 2 passed.
- [ ] **Step 6: Commit** `pyproject.toml`, `uv.lock`, test (`git commit -m "Etap 4: pytest-xdist i -n 4 w addopts"`).

### Task 2: Przebieg na 4 procesach i naprawa kolizji

**Files:**
- Modify: zależnie od wyniku (podejrzani: `tests/api/test_search.py`, `tests/e2e/*`, `src/jersa/pages/*`, `src/jersa/fixtures/*`)

**Interfaces:**
- Consumes: Task 1 (`-n 4` domyślnie).
- Produces: `uv run pytest` zielone (148 passed) na 4 procesach; lista napraw w KNOWLEDGE (Task 4).

- [ ] **Step 1: Uruchom `uv run pytest` (4 procesy).** Zapisz czas i listę niezaliczonych (`-ra` je pokazuje). Expected: albo 148 passed, albo lista kolizji.
- [ ] **Step 2: Dla każdej niezaliczonej pary (test, kolizja) ustal przyczynę** (`superpowers:systematic-debugging`): uruchom test sam (`-n 0`), potem w parze z podejrzanym sąsiadem na `-n 2`. Przyczynę zapisz w jednym zdaniu (współdzielone dane, brak oczekiwania w UI, limit połączeń).
- [ ] **Step 3: Napraw przyczynę.** Test z własnym produktem zamiast danych seeda; asercja względem stanu sprzed akcji (ADR-013); w E2E oczekiwanie na element (`expect`) zamiast stałych czasów. Jeśli kolizja wymaga naprawy kodu frameworka, najpierw test w `tests/framework` (czerwony), potem poprawka.
- [ ] **Step 4: `serial` tylko wyjątkowo:** jeśli test z natury modyfikuje stan globalny sklepu, zarejestruj marker `serial` w `pyproject.toml` i oznacz test; opisz wyjątek w ADR (Task 4). Domyślnie ten krok pomijamy.
- [ ] **Step 5: Powtarzaj Step 1–3, aż `uv run pytest` da 148 passed.** Expected: 148 passed (lub więcej o testy dodane w tym zadaniu).
- [ ] **Step 6: `uv run ruff check` i `uv run ruff format --check`; commit** każdej naprawy osobno, z komunikatem o przyczynie.

### Task 3: Dowód niezależności (3 przebiegi i stan bazy)

**Files:** brak zmian w kodzie (chyba że wykryje coś Task 3).

**Interfaces:**
- Consumes: Task 2 zielone.
- Produces: zmierzone czasy (`-n 0` vs `-n 4`), wynik kontroli bazy do KNOWLEDGE.

- [ ] **Step 1: Czysty start:** `docker compose down -v` i `docker compose up -d --build --wait`. Zapisz md5 seeda (ta sama metoda co w Etapie 3: zapytanie o produkty seeda, zbiorczy skrót; sprawdź ostatni opis w `KNOWLEDGE.md` sekcja 6/8).
- [ ] **Step 2: Uruchom `uv run pytest` trzy razy z rzędu.** Expected: 3 × passed. Zapisz czasy.
- [ ] **Step 3: Po każdym przebiegu sprawdź w bazie:** 0 koszyków, 0 przechowalni, 0 zamówień, 0 produktów `test-*`, md5 seeda bez zmian. Expected: bez zmian.
- [ ] **Step 4: Zmierz `uv run pytest -n 0`** (punkt odniesienia z Task 1) i porównaj. Zapisz zysk. Sprawdź też liczbę połączeń do Postgresa w trakcie (`select count(*) from pg_stat_activity`) i że mieści się w limicie.
- [ ] **Step 5: `uv run pytest tests/framework` w CI-podobnych warunkach** (bez sklepu): jeśli wolniej niż w Task 1 Step 1, dodaj `-n 0` do kroku „Testy frameworka” w `.github/workflows/ci.yml` i zapisz powód.
- [ ] **Step 6: Gdy wyjdzie ślad lub flaky test:** wróć do Task 2 (nie przechodź dalej).

### Task 4: Dokumentacja i zamknięcie etapu

**Files:**
- Modify: `KNOWLEDGE.md` (sekcje 2, 4, 6 jeśli były problemy, 8, 9), `CLAUDE.md` (status, polecenia), `docs/komendy.md`, `README.md`, `.env.example`, ewentualnie `.github/workflows/ci.yml`

**Interfaces:** Consumes: wyniki z Task 2 i 3.

- [ ] **Step 1: `docs/komendy.md`:** sekcja 2 — `uv run pytest` działa na 4 procesach (podaj zmierzony czas); nowy wiersz „`uv run pytest -n 0`: jeden proces, do debugowania (`--pdb`, `-s`) i podglądu na żywo”; w sekcji 5 uwaga, że `--headed` i `HEADED=true` z `-n 4` otwierają 4 okna, więc do podglądu użyj `-n 0`.
- [ ] **Step 2: `.env.example`:** komentarz przy `HEADED`: „do podglądu użyj `-n 0`”. `README.md`: jedno zdanie o `-n 4` i `-n 0`.
- [ ] **Step 3: `KNOWLEDGE.md`:** sekcja 2 — odhacz Etap 3 i Etap 4; ADR-015 (wybór B, dystrybucja `load`, ewentualne wyjątki), wraz z polem „Na rozmowie” (1–3 proste zdania); sekcja 6 — problemy znalezione w Task 2; sekcja 8 — numerowane kroki; sekcja 9 — pytania z odpowiedziami: izolacja testów równoległych, `-n` i `load` vs `loadfile`, fixtury sesyjne per proces, co zrobić z testem, który pada tylko równolegle (z dowodem w projekcie).
- [ ] **Step 4: `CLAUDE.md`:** status („Etap 4 zrobiony <data>, następny Etap 5”), polecenia o `-n 0`.
- [ ] **Step 5: Sprawdź:** `uv run ruff check`, `uv run ruff format --check`, `uv run pytest` (zielone). Commit dokumentacji.
- [ ] **Step 6: Nie pushuj bez zgody.** Zapytaj właściciela o push gałęzi i PR do `main` (bramka); po zgodzie `git push -u origin etap-4-rownoleglosc` i `gh pr create`.
