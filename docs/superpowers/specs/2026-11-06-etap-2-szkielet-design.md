# Etap 2 — szkielet repo testów (projekt)

- **Data:** 2026-11-06
- **Status:** zatwierdzony 2026-11-06, do planu
- **Poprzedni etap:** Etap 1 zamknięty (sklep w Dockerze na `127.0.0.1:3100`, Postgres na `127.0.0.1:5432`, STG wdrożony z `91b5669`)

## 1. Po co

Szkielet ma sprawić, że w Etapie 3 dopisuje się tylko testy. Adres sklepu, klient HTTP, połączenie z bazą, przeglądarka i sprawdzanie schematu są gotowe i każdy test dostaje je przez fixture.

Druga połowa celu to nauka i portfolio. Repo staje się publiczne na GitHubie. Każda decyzja ma ADR w `KNOWLEDGE.md`, a od pierwszego pushu działa prosty CI.

## 2. Cele

1. Struktura katalogów i konfiguracja projektu Pythona, gotowe na cztery poziomy testów.
2. Konfiguracja w jednym miejscu, czytana z `.env`, z walidacją i czytelnym błędem, gdy czegoś brakuje.
3. Fixtures: `settings`, `base_url`, `api_client`, `db`, `page` (z pytest-playwright), `assert_matches_schema`.
4. Po jednym teście `smoke` na każdym poziomie (contract, api, db, e2e). Te testy dowodzą, że dany element szkieletu działa na sklepie w Dockerze. Nie mają pokrywać funkcji sklepu.
5. Testy samego frameworka (`tests/framework/`): sprawdzają loader schematów i konfigurację bez uruchomionego sklepu.
6. ruff (linter i formatter) bez błędów.
7. Publiczne repo `ironz1/jersa_test_framework` na GitHubie i workflow GitHub Actions: ruff i testy frameworka przy każdym pushu i PR-ze.

## 3. Poza zakresem

- Właściwe scenariusze testowe i pełne schematy kontraktów: Etap 3.
- Tworzenie i sprzątanie danych, uruchamianie równoległe (pytest-xdist): Etap 4. Fixtures z Etapu 2 nie mogą jednak równoległości blokować.
- Sklep w Dockerze w CI, bramka na PR sklepu, raporty HTML i artefakty: Etap 5.
- Logowanie do `/api/admin/*`: Etap 3.
- mypy i pre-commit: decyzja po Etapie 3, gdy będzie więcej kodu.

## 4. Antycele (porażka, nawet jeśli działa)

Lista powstała z przeglądu poprzedniego frameworka użytkownika:

- **Stan globalny.** Zmienne modułu ani atrybuty klas przekazujące dane między testami są zabronione. Fixture zwraca obiekt, test go dostaje.
- **Zależność od kolejności testów.** Każdy test działa sam i w dowolnej kolejności.
- **Sekrety w repo.** Repo jest publiczne, więc w gicie jest tylko `.env.example`.
- **Jeden wielki `conftest.py`.** Fixtures są w modułach według odpowiedzialności.
- **Działa tylko u autora.** Wszystkie adresy przychodzą z konfiguracji, a jedna komenda instaluje całe środowisko.
- **Nadmiarowe abstrakcje.** Bez klasy `BaseTest`, bez własnych nakładek na Playwright i bez „frameworka we frameworku”.

## 5. Ograniczenia

- Laptop z Windows 11, Git Bash i PowerShell. CI na `ubuntu-latest`. Ścieżki i polecenia muszą działać w obu.
- Repo jest **publiczne** razem z całą historią, w tym `KNOWLEDGE.md`, `CLAUDE.md` i `docs/`. Autor commitów: `ironz1 <70520200+ironz1@users.noreply.github.com>`, ustawiony w `git config` tylko tego repo.
- Sklep jest prywatny i w Etapie 2 CI go nie potrzebuje.
- Testy smoke wymagają działającego `docker compose up -d --build --wait`.
- Konwencje z `CLAUDE.md`: markery `smoke`, `regression`, `contract`; schematy z `additionalProperties: false` spisane z prawdziwych odpowiedzi; prefiks uuid i sprzątanie po ID od Etapu 4.

## 6. Decyzje

Decyzje użytkownika:
- prosty CI z linterem już w Etapie 2 (zamiast dopiero w Etapie 5);
- repo publiczne razem z plikami MD i historią;
- adres zastępczy GitHuba zamiast prywatnego adresu e-mail;
- wybory techniczne należą do wykonawcy i każdy ma ADR z alternatywami.

Moje decyzje (do sprawdzenia przy czytaniu; każda trafi do `KNOWLEDGE.md` jako ADR):

| # | Decyzja | Odrzucone alternatywy | Dlaczego |
|---|---|---|---|
| D1 | **Python 3.12** instalowany przez uv | systemowy 3.11; 3.13 | 3.12 to stabilna wersja wspierana przez wszystkie biblioteki stacku. Ta sama wersja lokalnie i w CI. uv instaluje ją bez zmiany systemowego Pythona |
| D2 | **uv + `pyproject.toml` + `uv.lock`** | `requirements.txt` + pip + venv; Poetry | Jeden plik konfiguracji, zablokowane wersje (powtarzalna instalacja), szybki start w CI. `uv export` wygeneruje `requirements.txt`, gdyby był potrzebny |
| D3 | **Konfiguracja pytest i ruff w `pyproject.toml`** | `pytest.ini`, `ruff.toml` | Wszystko w jednym pliku. Zmienia docelową strukturę z `CLAUDE.md` (`pytest.ini` i `requirements.txt` znikają) |
| D4 | **pydantic-settings** dla konfiguracji | `python-dotenv` + `os.getenv`; dataclass | Typy i walidacja: zły URL albo brak `BASE_URL` daje czytelny błąd przy starcie, a nie w połowie testu |
| D5 | **psycopg 3** (`psycopg[binary]`) | psycopg2 | Aktywnie rozwijany następca, prostsze API, a `[binary]` nie wymaga kompilatora na Windows. Zmienia stack z `CLAUDE.md` |
| D6 | **Kod frameworka w pakiecie `src/jersa/`**, importowany przez `pythonpath = ["src"]` w konfiguracji pytest | płaskie `src/{clients,...}`; instalacja pakietu | Nazwy w rodzaju `clients` czy `db` jako pakiety najwyższego poziomu mogłyby kolidować z bibliotekami. Jeden pakiet `jersa` tego unika |
| D7 | **Fixtures w modułach `src/jersa/fixtures/*.py`**, ładowanych przez `pytest_plugins` w głównym `conftest.py` | wszystko w `conftest.py` | Główny `conftest.py` zostaje krótki, a każda fixture ma swoje miejsce (antycel: wielki `conftest.py`) |
| D8 | **CI: ruff i `pytest tests/framework`**, bez Dockera | sam ruff; od razu Docker | Kilkadziesiąt sekund, nie wymaga dostępu do prywatnego repo sklepu. Docker w CI to Etap 5 |
| D9 | **Bez pytest-html i pytest-xdist w Etapie 2** | instalacja wszystkiego od razu | Dochodzą w etapach, które ich używają (4 i 5) |
| D10 | **Minimalny `README.md`** (co to jest, jak uruchomić) | README dopiero w Etapie 7 | Publiczne repo bez README źle wygląda w portfolio. Pełna dokumentacja nadal w Etapie 7 |

## 7. Projekt szkieletu

### Struktura

```
pyproject.toml  uv.lock  .python-version  README.md
conftest.py                       # pytest_plugins i fixture base_url
src/jersa/
  config.py                       # Settings (pydantic-settings)
  clients/api_client.py           # ApiClient
  db/connection.py                # połączenie psycopg 3
  schemas/loader.py               # wczytanie schematów i walidacja
  pages/product_page.py           # pierwszy page object
  fixtures/{config,api,db,schemas}.py
schemas/search.json  schemas/product.json
tests/contract/test_search_contract.py
tests/api/test_cart_smoke.py
tests/db/test_seed_smoke.py
tests/e2e/test_product_page_smoke.py
tests/framework/test_schema_loader.py  tests/framework/test_settings.py
.github/workflows/ci.yml
```

### Konfiguracja (`Settings`)
- Pola: `base_url` (wymagane), `database_url` (opcjonalne), `admin_password` (opcjonalne, na Etap 3). Czytane z `.env` i zmiennych środowiskowych (zmienne środowiskowe wygrywają, co przyda się w CI).
- Fixture `settings` o zasięgu `session`.
- `.env.example` zostaje źródłem prawdy o nazwach zmiennych.

### Fixtures
- **`base_url`** (`session`): nadpisuje fixture z pytest-base-url, z której korzysta pytest-playwright, i zwraca `settings.base_url`. Definiowana wprost w głównym `conftest.py`, bo fixture z `conftest.py` na pewno wygrywa z fixture z zainstalowanej wtyczki. Dzięki temu `page.goto("/produkt/...")` działa ze ścieżką względną.
- **`api_client`** (`function`): nowy `ApiClient` na każdy test, czyli nowa sesja `requests` i nowe ciasteczka. Koszyk i wishlist są przypisane do ciasteczka, więc to daje izolację za darmo (wniosek z Etapu 0). `ApiClient` ma metody `get/post/patch/delete(path, **kwargs)`, sam dokleja `base_url`, ma domyślny `timeout` (10 s) i **nie** rzuca wyjątku na statusy 4xx/5xx, bo status sprawdza test.
- **`db`** (`session`): połączenie psycopg 3 w trybie autocommit, wiersze jako słowniki. Jeśli `database_url` nie jest ustawione, testy używające `db` są **pomijane** z komunikatem (np. na STG bez dostępu do bazy), a nie kończą się błędem. Na koniec sesji połączenie jest zamykane. W Etapie 2 tylko odczyt.
- **`assert_matches_schema(instance, name)`**: wczytuje `schemas/<name>.json` (Draft 2020-12), rozwiązuje `$ref` między plikami (np. `search.json` → `product.json`) i przy niezgodności kończy test komunikatem ze ścieżką do błędnego pola. Schematy są cache'owane na czas sesji.
- **`page`**: z pytest-playwright, bez nakładek. Domyślnie tylko Chromium.

### Testy smoke (marker `smoke`)
| Poziom | Test | Co dowodzi |
|---|---|---|
| contract | `GET /api/commerce/search?q=castello` zgodne z `schemas/search.json` (marker także `contract`) | loader schematów, `$ref`, `api_client` |
| api | `GET /api/commerce/cart` → 200, puste `lines`, ustawione ciasteczko `jersa_cart` | `api_client`, izolacja przez sesję |
| db | w `ProductRow` istnieje `zakiet-castello` | `db`, konfiguracja `database_url` |
| e2e | strona `/produkt/zakiet-castello` ma nagłówek `h1` „Żakiet CASTELLO” | `page`, `base_url`, pierwszy page object |

Schematy `search.json` i `product.json` są spisane z prawdziwej odpowiedzi z Dockera, z `additionalProperties: false`. Pola różniące się między DEV i STG (np. `isNew`) są w schemacie typem, a nie wartością. Odpowiedź z 2026-11-06 ma 22 pola produktu, w tym pola nowsze niż `docs/api-reference.md` (np. `lookImages`, `relatedSlugs`). `compareAtPrice` i `sizeChartSrc` bywają `null`, więc ich typ to np. `["object", "null"]`. Rozbieżności z `docs/api-reference.md` trzeba tam odnotować.

### Testy frameworka (`tests/framework/`, bez sklepu)
- Loader: poprawny obiekt przechodzi; dodatkowe pole, brak wymaganego pola i zły typ dają błąd z czytelną ścieżką; `$ref` do drugiego pliku działa.
- `Settings`: wymagane `BASE_URL` (brak → błąd walidacji), zmienna środowiskowa nadpisuje `.env`, puste `DATABASE_URL` oznacza „brak bazy”.

### CI (`.github/workflows/ci.yml`)
- Wyzwalacze: `push` i `pull_request` na `main`.
- Kroki: checkout → setup-uv → `uv sync --locked` → `ruff check` → `ruff format --check` → `pytest tests/framework`.
- Bez sekretów i bez Dockera.

### Markery i ustawienia pytest
- Zarejestrowane `smoke`, `regression`, `contract` z `--strict-markers` (literówka w markerze to błąd, a nie cichy brak testów).
- `testpaths = ["tests"]`, `pythonpath = ["src"]`.

### GitHub
- Repo `ironz1/jersa_test_framework`, **publiczne**, push gałęzi `main` z obecną historią.
- **Utworzenie repo i pierwszy push wymagają wyraźnego polecenia użytkownika** w trakcie wykonania. Wcześniej trzeba sprawdzić, że w historii i plikach nie ma sekretów ani prywatnego adresu e-mail.
- Użytkownik w ustawieniach GitHuba włącza ukrywanie adresu e-mail i blokadę pushy, które by go ujawniały.

### Dokumentacja
- `KNOWLEDGE.md`: ADR-008…ADR-011 (zależności i wersja Pythona; konfiguracja i układ kodu; psycopg 3; CI od Etapu 2), notatki Etapu 2 w sekcji 2, kroki w sekcji 8, problemy w sekcji 6. Pole „Na rozmowie” zostaje dla użytkownika.
- `CLAUDE.md`: stack (psycopg 3, uv), docelowa struktura (`pyproject.toml` zamiast `pytest.ini` i `requirements.txt`), status.

## 8. Kryteria akceptacji

1. `uv sync` i `uv run playwright install chromium` na czystym klonie instalują wszystko.
2. Przy działającym Dockerze `uv run pytest -m smoke` daje 4 zielone testy.
3. Bez `DATABASE_URL` test db jest pomijany z komunikatem, a pozostałe przechodzą.
4. `uv run pytest tests/framework` przechodzi bez uruchomionego sklepu.
5. `uv run ruff check` i `uv run ruff format --check` nie zgłaszają błędów.
6. Celowo zepsuty schemat (np. usunięte pole) daje czerwony test contract z czytelną ścieżką do pola. Sprawdzone raz ręcznie, bez commita.
7. Na GitHubie workflow `ci` jest zielony na `main`.
8. Repo jest publiczne, nie zawiera sekretów, a wszystkie commity mają adres zastępczy.

## 9. Do decyzji wykonawcy

- Dokładne nazwy funkcji i klas pomocniczych, układ komunikatów błędów, reguły ruff ponad domyślne (proponowane: `E`, `F`, `I`, `B`, `UP`, `PT`).
- Selektor nagłówka produktu w page objecie, preferowany przez rolę i tekst (`get_by_role`).
- Kolejność zadań w planie.
