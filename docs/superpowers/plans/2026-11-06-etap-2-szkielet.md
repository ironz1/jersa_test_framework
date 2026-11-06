# Etap 2 — szkielet repo testów: plan wykonania

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** szkielet frameworka w Pythonie: konfiguracja, fixtures, po jednym teście smoke na każdym poziomie, testy frameworka, ruff i CI w publicznym repo na GitHubie.

**Architecture:** kod frameworka w pakiecie `src/jersa/` (importowany przez `pythonpath = ["src"]`), fixtures w modułach `src/jersa/fixtures/*.py` ładowanych przez `pytest_plugins` w głównym `conftest.py`. Testy smoke trafiają w sklep w Dockerze (`127.0.0.1:3100`, Postgres `127.0.0.1:5432`); testy frameworka (`tests/framework/`) nie potrzebują sklepu i to je uruchamia CI.

**Tech Stack:** Python 3.12 (uv), pytest, pytest-playwright, requests, psycopg 3, jsonschema (Draft 2020-12 + `referencing`), pydantic-settings, ruff, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-06-etap-2-szkielet-design.md`

## Global Constraints

- Python **3.12**, zależności przez **uv** w `pyproject.toml` + `uv.lock`; bez `requirements.txt` i `pytest.ini`.
- Zakaz stanu globalnego: żadnych zmiennych modułu ani atrybutów klas przekazujących dane między testami; fixture zwraca obiekt.
- W gicie tylko `.env.example`; repo będzie **publiczne** razem z historią.
- Autor commitów: `ironz1 <70520200+ironz1@users.noreply.github.com>` (już ustawione w `git config` repo; nie zmieniać).
- Każdy commit kończy się linią `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Markery: `smoke`, `regression`, `contract`, z `--strict-markers`.
- Schematy: `additionalProperties: false` na każdym poziomie obiektu, spisane z prawdziwej odpowiedzi.
- Bez pytest-html, pytest-xdist, mypy, pre-commit (spec §3, D9).
- Testy smoke wymagają `docker compose up -d --build --wait` (sklep na `http://localhost:3100`).
- Utworzenie repo na GitHubie i push **tylko na wyraźne polecenie użytkownika**.
- Praca na gałęzi `etap-2-szkielet` od `main`.

## Review Focus

1. **pytest uruchomiony z innego katalogu** (IDE uruchamia z `tests/…`) → `.env` nadal znaleziony, bo ścieżka do niego jest absolutna od katalogu projektu. Test: Task 1, `test_env_file_points_to_project_root`.
2. **Brak `.env` i `BASE_URL`** (CI, świeży klon) → testy frameworka i tak działają; autouse `_verify_url` z pytest-base-url wymusza fixture `base_url`, więc `tests/framework/conftest.py` ją nadpisuje. Test: Task 6, przebieg CI bez `.env`; lokalnie `test_framework_tests_do_not_need_settings`.
3. **`BASE_URL` z ukośnikiem na końcu** (`http://localhost:3100/`) → brak `//` w adresach. Test: Task 1 (`test_trailing_slash_is_stripped`) i Task 3 (`test_url_joins_without_double_slash`).
4. **Sklep albo baza nie działają** → szybki, czytelny błąd zamiast zawieszenia: `ApiClient` ma domyślny timeout 10 s, `connect()` ma `connect_timeout=5`. Test: Task 3 (`test_requests_use_default_timeout`), Task 4 (`test_connect_passes_timeout_and_autocommit`).
5. **Literówka w nazwie schematu** → `FileNotFoundError` z listą dostępnych schematów, a nie `KeyError` z głębi biblioteki. Test: Task 2, `test_unknown_schema_name_lists_available`.

---

### Task 0: Gałąź robocza

- [ ] **Step 1:** `git switch -c etap-2-szkielet` (z czystego `main`). Expected: `Switched to a new branch 'etap-2-szkielet'`.

---

### Task 1: Projekt Pythona i konfiguracja (`Settings`)

**Files:**
- Create: `pyproject.toml`, `uv.lock`, `.python-version`, `conftest.py`, `src/jersa/__init__.py`, `src/jersa/config.py`, `src/jersa/fixtures/__init__.py`, `src/jersa/fixtures/config.py`, `tests/framework/conftest.py`, `tests/framework/test_settings.py`

**Interfaces:**
- Produces: `jersa.config.Settings` (pydantic-settings) z polami `base_url: str`, `database_url: str | None`, `admin_password: SecretStr | None`; `jersa.config.PROJECT_ROOT: Path`; fixture `settings` (session) → `Settings`; fixture `base_url` (session, w głównym `conftest.py`) → `str` bez ukośnika na końcu.

- [ ] **Step 1: Utwórz projekt uv**

`uv init --bare --name jersa-test-framework --python 3.12`, `uv python pin 3.12`, potem `uv add pytest pytest-playwright requests "psycopg[binary]" jsonschema pydantic-settings` i `uv add --dev ruff`. W `pyproject.toml` dopisz:
- `[tool.uv] package = false`
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `pythonpath = ["src"]`, `addopts = "--strict-markers -ra"`, `markers = ["smoke: szybkie sprawdzenie, że element działa", "regression: pełny zestaw regresji", "contract: zgodność odpowiedzi API ze schematem"]`
- `[tool.ruff]`: `target-version = "py312"`, `line-length = 100`; `[tool.ruff.lint] select = ["E", "F", "I", "B", "UP", "PT"]`

Expected: `uv run python --version` → `Python 3.12.x`.

- [ ] **Step 2: Napisz failing testy `tests/framework/test_settings.py`**

Każdy test buduje `Settings(_env_file=<plik w tmp_path albo None>)` i czyści zmienne `BASE_URL`, `DATABASE_URL`, `ADMIN_PASSWORD` przez `monkeypatch.delenv(..., raising=False)`, żeby lokalny `.env` i system nie wpływały na wynik.

```python
def test_reads_values_from_env_file(tmp_path, clean_env):
    env = tmp_path / ".env"
    env.write_text(
        "BASE_URL=http://localhost:3100\nDATABASE_URL=postgresql://u:p@localhost:5432/db\n"
    )
    s = Settings(_env_file=env)
    assert s.base_url == "http://localhost:3100"
    assert s.database_url == "postgresql://u:p@localhost:5432/db"


def test_environment_variable_overrides_env_file(tmp_path, clean_env, monkeypatch):
    # plik: BASE_URL=http://from-file:1 ; env: BASE_URL=http://from-env:2
    assert Settings(_env_file=env).base_url == "http://from-env:2"


def test_missing_base_url_raises(clean_env):
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_base_url_raises(clean_env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "localhost:3100")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_trailing_slash_is_stripped(clean_env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://localhost:3100/")
    assert Settings(_env_file=None).base_url == "http://localhost:3100"


def test_empty_database_url_means_no_database(clean_env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://localhost:3100")
    monkeypatch.setenv("DATABASE_URL", "")
    assert Settings(_env_file=None).database_url is None


def test_ignores_unrelated_keys(tmp_path, clean_env):
    # plik zawiera też STOREFRONT_PATH=..., APP_PORT=3100 (jak prawdziwy .env)
    assert Settings(_env_file=env).base_url == "http://localhost:3100"


def test_env_file_points_to_project_root():
    env_file = Path(Settings.model_config["env_file"])
    assert env_file.is_absolute()
    assert env_file.name == ".env"
    assert (env_file.parent / "pyproject.toml").exists()


def test_framework_tests_do_not_need_settings(base_url):
    assert base_url == "http://framework-tests.invalid"
```

`clean_env` to fixture w tym pliku, usuwająca trzy zmienne.

- [ ] **Step 3: Uruchom.** `uv run pytest tests/framework -q` → FAIL (`ModuleNotFoundError: jersa.config` / brak fixture).

- [ ] **Step 4: Zaimplementuj**
- `src/jersa/config.py`: `PROJECT_ROOT = Path(__file__).resolve().parents[2]`; `class Settings(BaseSettings)` z `model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")`. Walidator `base_url`: schemat `http`/`https` i niepusty host (przez `urllib.parse.urlparse`), zwraca wartość bez końcowego `/`. Walidator `database_url` (mode `before`): pusty string → `None`.
- `src/jersa/fixtures/config.py`: fixture `settings(scope="session") -> Settings`.
- `conftest.py`: `pytest_plugins = ["jersa.fixtures.config"]` (kolejne moduły dopisują następne zadania) i fixture `base_url(settings) -> str` (session) z docstringiem, że nadpisuje fixture pytest-base-url.
- `tests/framework/conftest.py`: fixture `base_url() -> str` (session) zwracająca `"http://framework-tests.invalid"` z komentarzem: autouse `_verify_url` z pytest-base-url wymusza `base_url`, a testy frameworka nie mogą zależeć od `.env`.

- [ ] **Step 5: Uruchom.** `uv run pytest tests/framework -q` → 9 passed. `uv run ruff check` i `uv run ruff format --check` → bez błędów (najpierw `uv run ruff format`).

- [ ] **Step 6: Commit** `Etap 2: projekt uv i konfiguracja Settings` (pliki z listy).

---

### Task 2: Loader schematów i `assert_matches_schema`

**Files:**
- Create: `src/jersa/schemas/__init__.py`, `src/jersa/schemas/loader.py`, `src/jersa/fixtures/schemas.py`, `tests/framework/test_schema_loader.py`
- Modify: `conftest.py` (dopisz `"jersa.fixtures.schemas"` do `pytest_plugins`)

**Interfaces:**
- Produces: `jersa.schemas.loader.SCHEMAS_DIR: Path` (= `PROJECT_ROOT / "schemas"`); `class SchemaRegistry(schemas_dir: Path)` z metodą `errors(instance: object, name: str) -> list[str]`; fixture `schema_registry` (session) → `SchemaRegistry(SCHEMAS_DIR)`; fixture `assert_matches_schema` (function) → `Callable[[object, str], None]`, która przy błędach woła `pytest.fail` z listą błędów, każdy w osobnej linii.
- Konwencja: `name` bez rozszerzenia (`"search"` → `search.json`); każdy plik schematu ma `"$id": "<nazwa pliku>"`, a odwołania między plikami to `"$ref": "<nazwa pliku>"`.

- [ ] **Step 1: Napisz failing testy**

Fixture `schemas_dir(tmp_path)` zapisuje dwa pliki: `item.json` (`$id: "item.json"`, obiekt, `required: ["name"]`, `name: string`, `additionalProperties: false`) i `list.json` (`$id: "list.json"`, obiekt z `items: {type: array, items: {$ref: "item.json"}}`, `additionalProperties: false`).

```python
def test_valid_instance_has_no_errors(schemas_dir):
    assert SchemaRegistry(schemas_dir).errors({"items": [{"name": "a"}]}, "list") == []


def test_extra_property_reported_with_path(schemas_dir):
    errors = SchemaRegistry(schemas_dir).errors({"items": [{"name": "a", "x": 1}]}, "list")
    assert len(errors) == 1
    assert errors[0].startswith("$.items[0]: ")
    assert "'x' was unexpected" in errors[0]


def test_missing_required_property_reported(schemas_dir):
    errors = SchemaRegistry(schemas_dir).errors({"items": [{}]}, "list")
    assert errors == ["$.items[0]: 'name' is a required property"]


def test_wrong_type_reported(schemas_dir):
    errors = SchemaRegistry(schemas_dir).errors({"items": [{"name": 1}]}, "list")
    assert errors == ["$.items[0].name: 1 is not of type 'string'"]


def test_unknown_schema_name_lists_available(schemas_dir):
    with pytest.raises(FileNotFoundError, match=r"nope.*item, list"):
        SchemaRegistry(schemas_dir).errors({}, "nope")
```

- [ ] **Step 2: Uruchom.** `uv run pytest tests/framework/test_schema_loader.py -q` → FAIL (brak modułu).

- [ ] **Step 3: Zaimplementuj `SchemaRegistry`**
Konstruktor wczytuje wszystkie `*.json` z katalogu do `referencing.Registry` (zasób per plik, klucz = nazwa pliku, specyfikacja Draft 2020-12). `errors()` buduje `Draft202012Validator(schema, registry=...)`, zbiera `iter_errors`, formatuje `"<ścieżka>: <message>"`, gdzie ścieżka to `$` plus `.klucz` dla kluczy i `[i]` dla indeksów z `error.absolute_path`; wynik posortowany. Nieznana nazwa → `FileNotFoundError(f"Brak schematu '{name}'. Dostępne: {', '.join(sorted(nazwy))}")`.

- [ ] **Step 4: Uruchom.** → 5 passed; cały `tests/framework` zielony; ruff bez błędów.

- [ ] **Step 5: Commit** `Etap 2: loader schematów z czytelnymi błędami`.

---

### Task 3: Klient API i smoke koszyka

**Files:**
- Create: `src/jersa/clients/__init__.py`, `src/jersa/clients/api_client.py`, `src/jersa/fixtures/api.py`, `tests/framework/test_api_client.py`, `tests/api/test_cart_smoke.py`
- Modify: `conftest.py` (`"jersa.fixtures.api"`)

**Interfaces:**
- Consumes: fixture `base_url` (Task 1).
- Produces: `class ApiClient(base_url: str, timeout: float = 10.0)` z metodami `url(path: str) -> str`, `get/post/patch/delete(path: str, **kwargs) -> requests.Response`, właściwością `cookies -> requests.cookies.RequestsCookieJar` i `close() -> None`; fixture `api_client` (function) → nowy `ApiClient` na test, zamykany po teście. Klient **nie** rzuca wyjątku na 4xx/5xx.

- [ ] **Step 1: Napisz failing testy frameworka**

```python
def test_url_joins_without_double_slash():
    assert ApiClient("http://h:1").url("/api/x") == "http://h:1/api/x"


def test_path_must_start_with_slash():
    with pytest.raises(ValueError):
        ApiClient("http://h:1").url("api/x")


def test_requests_use_default_timeout(monkeypatch):
    client = ApiClient("http://h:1")
    seen = {}
    monkeypatch.setattr(
        client._session, "request", lambda method, url, **kw: seen.update(kw) or "resp"
    )
    client.get("/x")
    assert seen["timeout"] == 10.0
```

- [ ] **Step 2: Uruchom** → FAIL. **Step 3: Zaimplementuj** `ApiClient` na `requests.Session` (atrybut `_session`); `timeout` przekazywany, chyba że wywołujący poda własny (`kwargs.setdefault`). **Step 4:** testy frameworka zielone.

- [ ] **Step 5: Smoke `tests/api/test_cart_smoke.py`**

```python
@pytest.mark.smoke
def test_new_session_gets_empty_cart(api_client):
    response = api_client.get("/api/commerce/cart")
    assert response.status_code == 200
    assert response.json()["lines"] == []
    assert "jersa_cart" in api_client.cookies
```

Run (Docker działa): `uv run pytest tests/api -q` → 1 passed.

- [ ] **Step 6: Commit** `Etap 2: klient API i smoke koszyka`.

---

### Task 4: Połączenie z bazą i smoke seedu

**Files:**
- Create: `src/jersa/db/__init__.py`, `src/jersa/db/connection.py`, `src/jersa/fixtures/db.py`, `tests/framework/test_db_connection.py`, `tests/db/test_seed_smoke.py`
- Modify: `conftest.py` (`"jersa.fixtures.db"`)

**Interfaces:**
- Consumes: fixture `settings` (Task 1).
- Produces: `connect(database_url: str) -> psycopg.Connection` (autocommit, `row_factory=dict_row`, `connect_timeout=5`); fixture `db` (session) → połączenie albo `pytest.skip("DATABASE_URL nie jest ustawione, pomijam test bazy")`; zamykane na koniec sesji.

- [ ] **Step 1: Failing test frameworka**

```python
def test_connect_passes_timeout_and_autocommit(monkeypatch):
    seen = {}
    monkeypatch.setattr(psycopg, "connect", lambda url, **kw: seen.update(url=url, **kw) or "conn")
    assert connect("postgresql://x") == "conn"
    assert seen["autocommit"] is True
    assert seen["connect_timeout"] == 5
    assert seen["row_factory"] is dict_row
```

- [ ] **Step 2–4:** FAIL → implementacja (`connection.py` importuje moduł `psycopg`, nie samą funkcję, żeby monkeypatch działał) → PASS.

- [ ] **Step 5: Smoke `tests/db/test_seed_smoke.py`**

```python
@pytest.mark.smoke
def test_seed_contains_castello(db):
    rows = db.execute(
        'SELECT slug FROM "ProductRow" WHERE slug = %s', ("zakiet-castello",)
    ).fetchall()
    assert rows == [{"slug": "zakiet-castello"}]
```

Run: `uv run pytest tests/db -q` → 1 passed. Potem `DATABASE_URL= uv run pytest tests/db -rs` → 1 skipped z komunikatem o `DATABASE_URL`.

- [ ] **Step 6: Commit** `Etap 2: połączenie z bazą i smoke seedu`.

---

### Task 5: Kontrakt wyszukiwarki

**Files:**
- Create: `schemas/product.json`, `schemas/search.json`, `tests/contract/test_search_contract.py`
- Modify: `docs/api-reference.md` (sekcja Product i search)

**Interfaces:**
- Consumes: `api_client` (Task 3), `assert_matches_schema` (Task 2).

- [ ] **Step 1: Pobierz prawdziwą odpowiedź** `curl -s "http://127.0.0.1:3100/api/commerce/search?q=castello" | python -m json.tool`. Produkt ma 22 pola (stan 2026-11-06).

- [ ] **Step 2: Napisz test**

```python
@pytest.mark.smoke
@pytest.mark.contract
def test_search_matches_contract(api_client, assert_matches_schema):
    response = api_client.get("/api/commerce/search", params={"q": "castello"})
    assert response.status_code == 200
    body = response.json()
    assert body["products"], "seed powinien zwrócić CASTELLO"
    assert_matches_schema(body, "search")
```

Run → FAIL (`Brak schematu 'search'`).

- [ ] **Step 3: Spisz schematy.** `product.json` (`$id: "product.json"`): wszystkie pola z odpowiedzi w `required`, `additionalProperties: false` na każdym zagnieżdżonym obiekcie (`price`, `opis`, elementy `images`, `sizes`, …), typy zamiast wartości (`isNew: boolean`), `compareAtPrice` i `sizeChartSrc` jako typ obiektu/stringu lub `null` zgodnie z tym, czym są, gdy nie są `null` (sprawdź w kodzie sklepu `src/commerce/types.ts`). `search.json` (`$id: "search.json"`): `{products: array of $ref "product.json"}`, `required: ["products"]`, `additionalProperties: false`.

- [ ] **Step 4: Uruchom.** `uv run pytest tests/contract -q` → 1 passed. Sprawdź też na STG: `BASE_URL=https://jersa-storefront.vercel.app uv run pytest tests/contract -q` → 1 passed (dane różne, kształt ten sam).

- [ ] **Step 5: Ręczny test czerwony (bez commita).** Usuń jedno pole z `required` i `properties` w `product.json` → test pada z linią `$.products[0]: Additional properties are not allowed ('<pole>' was unexpected)`. Przywróć (`git checkout schemas/product.json`).

- [ ] **Step 6:** W `docs/api-reference.md` opisz aktualne pola Product (nowe: m.in. `lookImages`, `relatedSlugs`) i wskaż `schemas/` jako źródło prawdy.

- [ ] **Step 7: Commit** `Etap 2: kontrakt wyszukiwarki`.

---

### Task 6: Page object i smoke E2E

**Files:**
- Create: `src/jersa/pages/__init__.py`, `src/jersa/pages/product_page.py`, `tests/e2e/test_product_page_smoke.py`

**Interfaces:**
- Consumes: `page` (pytest-playwright), `base_url` (Task 1).
- Produces: `class ProductPage(page: Page)` z `open(slug: str) -> None` (`page.goto(f"/produkt/{slug}")`) i właściwością `heading -> Locator` (`get_by_role("heading", level=1)`).

- [ ] **Step 1:** `uv run playwright install chromium`.

- [ ] **Step 2: Test**

```python
@pytest.mark.smoke
def test_product_page_shows_name(page):
    product = ProductPage(page)
    product.open("zakiet-castello")
    expect(product.heading).to_have_text("Żakiet CASTELLO")
```

Run → FAIL (brak modułu) → **Step 3:** implementacja → **Step 4:** `uv run pytest tests/e2e -q` → 1 passed.

- [ ] **Step 5: Pełny smoke.** `uv run pytest -m smoke -q` → 4 passed. `uv run pytest tests/framework -q` → zielone. ruff bez błędów.

- [ ] **Step 6: Commit** `Etap 2: page object i smoke E2E`.

---

### Task 7: CI, README i dokumentacja

**Files:**
- Create: `.github/workflows/ci.yml`, `README.md`
- Modify: `KNOWLEDGE.md`, `CLAUDE.md`, `.env.example` (tylko komentarz, jeśli potrzebny)

- [ ] **Step 1: Workflow `ci.yml`**: `name: ci`; `on: push` i `pull_request` na `main`; job `lint-and-framework-tests` na `ubuntu-latest`: `actions/checkout@v4` → `astral-sh/setup-uv@v6` → `uv sync --locked` → `uv run ruff check` → `uv run ruff format --check` → `uv run pytest tests/framework`. Bez sekretów, bez `.env`.

- [ ] **Step 2: Symulacja CI lokalnie.** Tymczasowo zmień nazwę `.env` na `.env.bak`, uruchom te same cztery komendy, przywróć `.env`. Expected: wszystkie przechodzą (Review Focus 2).

- [ ] **Step 3: `README.md`**: jednym akapitem co to jest (framework dla jersa-storefront, portfolio SDET), wymagania (uv, Docker), uruchomienie (`docker compose up -d --build --wait`, `cp .env.example .env`, `uv sync`, `uv run playwright install chromium`, `uv run pytest -m smoke`), struktura katalogów, odnośnik do `KNOWLEDGE.md`.

- [ ] **Step 4: `KNOWLEDGE.md`**: ADR-008 (Python 3.12 + uv + `pyproject.toml`, D1–D3), ADR-009 (konfiguracja pydantic-settings, pakiet `src/jersa`, fixtures w modułach, D4, D6, D7), ADR-010 (psycopg 3, D5), ADR-011 (CI od Etapu 2 bez Dockera, D8); pole „Na rozmowie” puste. Sekcja 2: notatki Etapu 2 (co powstało, wyniki weryfikacji). Sekcja 6: problemy napotkane w trakcie. Sekcja 8: kolejne kroki (np. „Szkielet z jednym testem na poziom”, „CI od pierwszego pushu”). Sekcja 1 i tabela narzędzi: psycopg2 → psycopg 3.

- [ ] **Step 5: `CLAUDE.md`**: stack (psycopg 3, uv, pydantic-settings), docelowa struktura (`pyproject.toml` + `uv.lock` zamiast `pytest.ini` i `requirements.txt`, `src/jersa/{clients,pages,db,schemas,fixtures}`, `tests/framework/`), status.

- [ ] **Step 6: Commit** `Etap 2: CI, README i dokumentacja`.

---

### Task 8: Scalenie i publikacja na GitHubie

- [ ] **Step 1: Kontrola przed publikacją.**
  - `git ls-files | grep -E '^\.env$'` → pusto.
  - `git log --all --format='%ae%n%ce' | sort -u` → jedna linia: `70520200+ironz1@users.noreply.github.com` (adres Claude jest tylko w treści commitów, w `Co-Authored-By`).
  - `git grep -nI -iE '<lokalne-części-prywatnych-adresów>|BEGIN (RSA|OPENSSH)|ghp_|sk-'` → pusto.
- [ ] **Step 2:** `git switch main && git merge --ff-only etap-2-szkielet && git branch -d etap-2-szkielet`.
- [ ] **Step 3: Zatrzymaj się i poproś użytkownika o polecenie publikacji.** Przypomnij o ustawieniach e-mail w GitHubie (Keep private + Block command line pushes).
- [ ] **Step 4 (po poleceniu):** `gh repo create ironz1/jersa_test_framework --public --source . --remote origin --push`. Expected: URL repo i wypchnięta gałąź `main`.
- [ ] **Step 5:** `gh run watch` (najnowszy przebieg `ci`) → success. Przy porażce: przeczytaj log (`gh run view --log-failed`), napraw na gałęzi, scal, wypchnij.
- [ ] **Step 6:** `KNOWLEDGE.md` sekcja 2: Etap 2 odhaczony z linkiem do repo; `CLAUDE.md` status → Etap 3. Commit `Etap 2: zamknięcie` i push (w ramach tego samego polecenia publikacji).
