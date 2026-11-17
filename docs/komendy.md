# Komendy: jak uruchamiać testy

Wszystkie komendy uruchamiasz w katalogu repo `jersa_test_framework`. Działają w PowerShell i w Git Bash, chyba że przy komendzie napisano inaczej.

## 1. Sklep w Dockerze

Testy sklepu wymagają działającego sklepu pod `127.0.0.1:3100`.

| Komenda | Co robi |
|---|---|
| `docker compose up -d --build --wait` | buduje i uruchamia sklep z bazą, czeka, aż będzie gotowy |
| `docker compose ps` | pokazuje, czy kontenery działają |
| `docker compose logs app` | logi sklepu |
| `docker compose down` | zatrzymuje sklep, baza zostaje |
| `docker compose down -v` | zatrzymuje sklep i kasuje bazę; następny start daje świeży seed |

`--build` jest potrzebne po każdej zmianie w kodzie sklepu. Bez niego Docker użyje starego obrazu.

Gdy Docker nie odpowiada: `docker version` ma pokazać wersję serwera. Jeśli zwraca błąd, zrestartuj Docker Desktop.

## 2. Uruchamianie testów

| Komenda | Co uruchamia |
|---|---|
| `uv run pytest` | wszystko, na 4 procesach (`-n 4` w `pyproject.toml`; ok. 15 s) |
| `uv run pytest -n 0` | wszystko w jednym procesie: do debugowania (`--pdb`, `-s`) i podglądu na żywo |
| `uv run pytest -m smoke` | ścieżkę krytyczną na każdym poziomie |
| `uv run pytest -m regression` | wszystkie testy sklepu |
| `uv run pytest -m contract` | testy kontraktu |
| `uv run pytest tests/framework` | testy samego frameworka; nie wymagają sklepu |

## 3. Jeden poziom, plik albo test

| Komenda | Co uruchamia |
|---|---|
| `uv run pytest tests/api` | jeden poziom: `contract`, `api`, `db` albo `e2e` |
| `uv run pytest tests/api/test_cart.py` | jeden plik |
| `uv run pytest tests/api/test_cart.py::test_change_quantity` | jeden test |
| `uv run pytest -k "wishlist"` | testy, które mają „wishlist” w nazwie |

## 4. Przydatne opcje

Opcje dopisujesz do dowolnej komendy `uv run pytest`, np. `uv run pytest tests/api -v -x`.

| Opcja | Co robi |
|---|---|
| `-v` | pokazuje nazwę każdego testu |
| `-x` | zatrzymuje się na pierwszej porażce |
| `--lf` | uruchamia tylko testy, które ostatnio padły |
| `-rs` | pokazuje, dlaczego test został pominięty |
| `--collect-only -q` | wypisuje testy bez uruchamiania |
| `-s` | pokazuje `print()` z testów; przy domyślnym `-n 4` nic nie wypisze, dodaj `-n 0` |

## 5. E2E z podglądem przeglądarki

Domyślnie testy idą na 4 procesach, więc `--headed` albo `HEADED=true` otworzy 4 okna naraz. Do podglądu jednego testu dodaj `-n 0`.

| Komenda | Co robi |
|---|---|
| `uv run pytest tests/e2e --headed -n 0` | pokazuje okno przeglądarki |
| `uv run pytest tests/e2e --headed --slowmo 300 -n 0` | jak wyżej, każdy krok zwolniony o 300 ms |
| `uv run pytest tests/e2e --tracing retain-on-failure` | zapisuje ślad (trace) tylko dla testów, które padły |
| `uv run playwright show-trace test-results/<folder>/trace.zip` | otwiera zapisany ślad: kroki, zrzuty ekranu, sieć |
| `uv run playwright install chromium` | instaluje przeglądarkę (raz, po `uv sync`) |

## 6. Jakość kodu

| Komenda | Co robi |
|---|---|
| `uv run ruff check` | linter: szuka błędów i złych praktyk |
| `uv run ruff check --fix` | linter z automatyczną poprawką tego, co da się poprawić |
| `uv run ruff format` | formatuje kod |
| `uv run ruff format --check` | sprawdza formatowanie bez zmian w plikach (tak robi CI) |

Bramka testów sklepu żyje w repo sklepu (`.github/workflows/tests.yml`): na PR-ze buduje sklep i uruchamia cały zestaw na 4 procesach. Zmianę zachowania sklepu razem z testami robi się parą gałęzi o **tej samej nazwie** w obu repo. Gałąź testów musi istnieć w momencie startu przebiegu (po jej późniejszym wypchnięciu uruchom przebieg ponownie), a obie gałęzie scala się razem: najpierw PR sklepu, zaraz po nim PR testów. Dopóki testy ze `main` nie nadążą za sklepem, każdy następny PR sklepu będzie czerwony. Gałąź testów tworzy właściciel.

CI repo testów uruchamia: `ruff check`, `ruff format --check` i `pytest tests/framework -n 0` (67 szybkich testów trwa w jednym procesie 0,5 s, a start 4 procesów dodaje ok. 4 s).

## 7. Macierz śledzenia wymagań

| Komenda | Co robi |
|---|---|
| `uv run python scripts/build_traceability.py` | buduje `docs/traceability-matrix.pdf` z `docs/traceability.json` |
| `uv run pytest tests/framework/test_traceability.py` | sprawdza spójność danych macierzy |

Jak dodać nowy test do macierzy: `KNOWLEDGE.md`, sekcja 7.

## 8. Zależności

| Komenda | Co robi |
|---|---|
| `uv sync` | instaluje zależności w wersjach z `uv.lock` |
| `uv add <pakiet>` | dodaje zależność do `pyproject.toml` i `uv.lock` |

## 9. Testy na STG

Tylko w Git Bash, bo komenda ustawia zmienne na czas jednego polecenia:

```bash
BASE_URL=https://jersa-storefront.vercel.app DATABASE_URL= uv run pytest tests/contract tests/api
```

Pusty `DATABASE_URL` jest konieczny. Testy z własnym produktem i testy bazy są wtedy pomijane. Bez niego test wstawiłby produkt do lokalnej bazy, a pytał o niego sklep na STG.
