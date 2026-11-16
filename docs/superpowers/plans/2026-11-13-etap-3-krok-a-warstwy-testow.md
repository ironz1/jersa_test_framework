# Etap 3, krok A — warstwy testów: plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ok. 75 nowych testów sklepu na czterech poziomach (kontrakt, API, baza, E2E) dla zachowań, które sklep ma dziś poprawnie, z własnym produktem na test i sprzątaniem po ID.

**Architecture:** Testy rozmawiają ze sklepem przez cienki klient `CommerceApi` (jedna metoda na endpoint). Testy, które coś kupują albo dodają opinię, dostają z fixture własny produkt wstawiony SQL-em (`test-<hex>`); teardown usuwa produkt razem z jego zamówieniami i opiniami. Seed jest tylko czytany.

**Tech Stack:** Python 3.12, uv, pytest 9, requests, psycopg 3, jsonschema (Draft 2020-12), pytest-playwright, ruff. Bez nowych zależności.

**Spec:** `docs/superpowers/specs/2026-11-13-etap-3-warstwy-testow-design.md`

## Global Constraints

- Sklep działa w Dockerze: `docker compose up -d --build --wait`, adres `http://127.0.0.1:3100`, baza `127.0.0.1:5432`. Repo sklepu jest tylko do odczytu.
- Nie otwieraj i nie wypisuj `.env`. Adresy przez `127.0.0.1`, nie `localhost`.
- Żadnych nowych zależności w `pyproject.toml`.
- Usuwamy tylko własne rekordy: produkty ze slugiem `test-…` oraz zamówienia i opinie tych produktów. Nigdy całe tabele, nigdy rekordy seeda.
- Oczekiwane wartości pochodzą z reguł biznesowych z tego planu, nie z tego, co sklep akurat zwraca. Jeśli sklep zwraca coś innego, to jest znalezisko: zapisz w ledgerze i zgłoś, nie dopasowuj testu.
- Żadnych liczb stanu magazynowego seeda na sztywno. Test odczytuje stan przed akcją i porównuje różnicę.
- Zero stanu globalnego. Fixtures w `src/jersa/fixtures/`, rejestrowane w `pytest_plugins` głównego `conftest.py`. Testy niezależne od kolejności.
- Markery: każdy test sklepu ma `regression`; testy ścieżki krytycznej dodatkowo `smoke`; testy kontraktu dodatkowo `contract`. `--strict-markers` jest włączone.
- Repo jest publiczne. W commitowanych plikach, nazwach testów i komentarzach nie opisuj otwartych błędów sklepu. Dwa pliki robocze w `docs/` są lokalne (wykluczone w `.git/info/exclude`) i nie są potrzebne do wykonania planu.
- Przed każdym commitem: `uv run ruff check` i `uv run ruff format --check` bez uwag. Komunikat commita po polsku, z trailerem `Co-Authored-By` z bieżącej instrukcji sesji. Bez pusha (push zleca właściciel).
- Macierz śledzenia (`docs/traceability.json`) jest źródłem nazw testów: funkcja testu nazywa się dokładnie tak jak w polu `tests` swojego przypadku, a jej docstring zaczyna się od ID przypadku, np. `"""A-CART-03: ten sam produkt i rozmiar dodany dwa razy zwiększa ilość."""`. Zmiana nazwy testu oznacza zmianę w JSON-ie w tym samym commicie.
- Praca na gałęzi `etap-3-krok-a`, nie na `main`.

## Review Focus

1. Teardown dostaje slug produktu z seeda (np. przez pomyłkę w teście) → nic nie zostaje usunięte, błąd `ValueError`. Test: `test_delete_refuses_slug_without_test_prefix` (Task 3).
2. Test pada w połowie, po złożeniu zamówienia → po teście nie zostaje ani zamówienie, ani produkt. Test: `test_delete_product_removes_its_orders_and_reviews` (Task 3).
3. Sklep dodaje do `ProductRow` wymaganą kolumnę → czytelny czerwony test z nazwą kolumny, zamiast błędu SQL w każdym teście. Test: `test_product_row_covers_required_columns` (Task 3).
4. Brak `DATABASE_URL` (np. STG) → testy z własnym produktem są pomijane z komunikatem, nie kończą się błędem. Weryfikacja w Task 3, krok 8.
5. Drugi i trzeci przebieg bez `down -v` → te same wyniki, stan magazynowy seeda bez zmian. Weryfikacja w Task 10, krok 1.

---

### Task 1: Przygotowanie

**Files:**
- Modify: `docker-compose.yml` (kotwica `x-storefront-env`)
- Modify: `tests/api/test_cart_smoke.py`, `tests/contract/test_search_contract.py`, `tests/db/test_seed_smoke.py`, `tests/e2e/test_product_page_smoke.py`
- Modify: `pyproject.toml` (opis markera `regression`)

- [ ] **Step 1:** `git switch -c etap-3-krok-a`. Zacommituj czekające zmiany: `CLAUDE.md`, `KNOWLEDGE.md`, spec, ten plan oraz macierz śledzenia (`docs/traceability.json`, `docs/traceability-matrix.pdf`, `src/jersa/traceability.py`, `scripts/build_traceability.py`, `tests/framework/test_traceability.py`): `Etap 3: projekt, plan, macierz śledzenia i reguły pracy`.
- [ ] **Step 2:** W `docker-compose.yml` dodaj do `x-storefront-env` linię `PAYU_MODE: mock` z komentarzem: tryb płatności testowej.
  Run: `docker compose config | grep PAYU_MODE` → Expected: dwie linie `PAYU_MODE: mock` (`db-init`, `app`).
- [ ] **Step 3:** Świeży sklep: `docker compose down -v` i `docker compose up -d --build --wait`. Expected: kod wyjścia 0, `app` healthy.
- [ ] **Step 4:** Do czterech istniejących testów smoke dodaj `@pytest.mark.regression`. W `pyproject.toml` opis markera: `regression: pełny zestaw regresji (każdy test sklepu)`.
  Run: `uv run pytest -m regression -q` → Expected: `4 passed`.
- [ ] **Step 5:** Commit: `Etap 3: PAYU_MODE w compose, marker regression na testach smoke`.

### Task 2: Klient `CommerceApi` i fixtures `shop`

**Files:**
- Create: `src/jersa/clients/commerce.py`
- Modify: `src/jersa/fixtures/api.py`
- Test: `tests/framework/test_commerce_api.py`

**Interfaces:**
- Consumes: `ApiClient.get/post/patch/delete(path, **kwargs) -> requests.Response` (`src/jersa/clients/api_client.py`).
- Produces (`jersa.clients.commerce`):
  - `EMAIL = "klientka@example.com"`, `MADE_TO_MEASURE = "made-to-measure"`
  - `SHIPPING = {"name": "Anna Nowak", "street": "Piotrkowska 1", "city": "Łódź", "postalCode": "90-001", "phone": "500000000"}`
  - `class CommerceApi(client: ApiClient)`, atrybut `client`. Każda metoda zwraca `requests.Response` i nie sprawdza statusu:

    | Metoda | Żądanie |
    |---|---|
    | `cart()` | `GET /api/commerce/cart` |
    | `add_to_cart(slug, size="36", quantity=1, custom_fit=False)` | `POST /api/commerce/cart`, json `{productSlug, size, quantity, customFit}` |
    | `set_quantity(line_id, quantity)` | `PATCH /api/commerce/cart`, json `{lineId, quantity}` |
    | `remove_line(line_id)` | `DELETE /api/commerce/cart`, json `{lineId}` |
    | `create_order(email=EMAIL, shipping=None)` | `POST /api/commerce/orders`, json `{email, shipping}`; `None` → kopia `SHIPPING` |
    | `start_payment(order_id)` | `POST /api/commerce/payu/start`, json `{orderId}` |
    | `notify(order_id, status)` | `POST /api/commerce/payu/notify`, json `{orderId, extOrderId, status}` (oba id takie same) |
    | `wishlist()` / `add_wish(slug)` / `remove_wish(slug)` | `GET` / `POST` / `DELETE /api/commerce/wishlist`, json `{productSlug}` |
    | `reviews(slug)` | `GET /api/commerce/reviews`, params `{productSlug}` |
    | `add_review(slug, author, body)` | `POST /api/commerce/reviews`, json `{productSlug, author, body}` |
    | `search(q)` | `GET /api/commerce/search`, params `{q}` |
- Produces (fixtures w `jersa.fixtures.api`): `make_shop() -> CommerceApi` (każde wywołanie to nowy `ApiClient`, czyli nowy klient sklepu z własnymi ciasteczkami; teardown zamyka wszystkie), `shop` = jedno `make_shop()`.

- [ ] **Step 1: Testy (najpierw).** W `tests/framework/test_commerce_api.py` atrapa klienta zapisująca wywołania:

```python
class RecordingClient:
    def __init__(self):
        self.calls = []

    def _record(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return "response"

    def get(self, path, **kwargs):
        return self._record("GET", path, **kwargs)

    # post, patch, delete analogicznie


def test_add_to_cart_sends_all_fields():
    client = RecordingClient()
    assert (
        CommerceApi(client).add_to_cart("p", size="38", quantity=2, custom_fit=True) == "response"
    )
    assert client.calls == [
        (
            "POST",
            "/api/commerce/cart",
            {"json": {"productSlug": "p", "size": "38", "quantity": 2, "customFit": True}},
        )
    ]
```

  Pozostałe testy w tym samym stylu: `test_add_to_cart_defaults` (size `"36"`, quantity `1`, customFit `False`), `test_create_order_defaults_to_standard_customer` (json `{"email": EMAIL, "shipping": SHIPPING}` i przekazany słownik nie jest tym samym obiektem co `SHIPPING`), `test_notify_sends_order_id_twice`, `test_search_uses_query_param` (`{"params": {"q": "x"}}`), `test_remove_wish_uses_delete`.
- [ ] **Step 2:** Run: `uv run pytest tests/framework/test_commerce_api.py -q` → Expected: błąd importu `jersa.clients.commerce`.
- [ ] **Step 3:** Zaimplementuj `CommerceApi` i fixtures wg bloku Interfaces.
- [ ] **Step 4:** Run: `uv run pytest tests/framework -q` → Expected: wszystkie zielone (33 dotychczasowe + 6 nowych).
- [ ] **Step 5:** Commit: `Etap 3: klient CommerceApi i fixtures shop`.

### Task 3: Własny produkt na test

**Files:**
- Create: `src/jersa/db/products.py`, `src/jersa/db/orders.py`, `src/jersa/fixtures/products.py`, `src/jersa/fixtures/orders.py`
- Modify: `conftest.py` (`pytest_plugins` + `"jersa.fixtures.products"`, `"jersa.fixtures.orders"`)
- Test: `tests/framework/test_own_product.py`, `tests/db/test_own_product_db.py`

**Interfaces:**
- Consumes: fixture `db` (`psycopg.Connection`, autocommit, wiersze jako słowniki), `CommerceApi`, fixture `shop`.
- Produces (`jersa.db.products`):
  - `OWN_PREFIX = "test-"`
  - `new_slug() -> str` — `"test-"` + 12 znaków hex z `uuid4`.
  - `@dataclass(frozen=True) class OwnProduct`: `slug: str`, `name: str`, `amount: int`, `promo_percent: int`, `stock: dict[str, int]`; właściwość `price -> int` = `round(amount * (100 - promo_percent) / 100)`.
  - `product_row(slug, *, name=None, amount=200, stock=None, promo_percent=0, made_to_measure=True, hidden=False) -> dict[str, object]` — klucze to nazwy kolumn `ProductRow`. Wartości:

    | Kolumna | Wartość |
    |---|---|
    | `id`, `slug` | `slug` |
    | `shoperId` | `0` |
    | `name` | `name` albo `f"Produkt testowy {slug[5:]}"` |
    | `amount` | `amount` |
    | `description` | `"Produkt testowy frameworka."` |
    | `opisJson` | JSON `{"intro": "Produkt testowy.", "features": ["test"], "sizesNote": "36–38", "material": "test"}` |
    | `imagesJson` | JSON `[{"src": "/preview/outfits/3.jpg", "alt": "Produkt testowy"}]` |
    | `categorySlugs` | `"[]"` (produkt nie pojawia się w kategoriach ani na stronie głównej) |
    | `sizeCodes` | JSON lista kluczy `stock`; domyślny `stock` to `{"36": 5, "38": 5}` |
    | `unavailable` | JSON lista rozmiarów ze stanem `<= 0` |
    | `stockBySize` | JSON `stock` |
    | `madeToMeasure`, `hidden` | z argumentów |
    | `isPromo` | `promo_percent > 0` |
    | `promoPercent` | `promo_percent` |
    | `isNew`, `isBestseller`, `offeredLessThan30Days` | `False` |
    | `lowestPriorAmount` | `0` |
    | `sizeChartSrc` | `""` |
    | `sortOrder` | `9999` |
    | `relatedSlugs`, `lookImagesJson` | `"[]"` |
  - `insert_product(conn, row: dict[str, object]) -> None` — `INSERT` z jawną listą kolumn z kluczy `row` (nazwy kolumn w cudzysłowach, wartości jako parametry).
  - `delete_product(conn, slug: str) -> None` — `ValueError`, gdy slug nie zaczyna się od `OWN_PREFIX` (przed jakimkolwiek SQL). Potem kolejno: `DELETE FROM "OrderRow" WHERE "linesJson" LIKE %s` z wzorcem `%"productSlug":"<slug>"%`, `DELETE FROM "ReviewRow" WHERE "productSlug" = %s`, `DELETE FROM "ProductRow" WHERE slug = %s`.
  - `read_stock(conn, slug) -> dict[str, int]` — sparsowane `stockBySize`.
- Produces (`jersa.db.orders`):
  - `get_order(conn, order_id) -> dict | None` — cały wiersz `OrderRow`.
  - `order_id_by_token(conn, public_token) -> str`.
  - `orders_of(conn, slug) -> list[dict]` — zamówienia produktu (ten sam wzorzec `LIKE`).
  - `backdate_expiry(conn, order_id) -> None` — `UPDATE "OrderRow" SET "expiresAt" = (now() at time zone 'utc') - interval '1 hour' WHERE id = %s`.
- Produces (fixtures):
  - `make_product(**overrides) -> OwnProduct` (argumenty jak `product_row` bez `slug`); teardown woła `delete_product` dla każdego utworzonego. Zależy od `db`, więc bez `DATABASE_URL` test jest pomijany.
  - `product` = `make_product()`.
  - `@dataclass(frozen=True) class PlacedOrder`: `id: str`, `public_token: str`, `size: str`, `quantity: int`; fixture `placed_order(shop, product) -> PlacedOrder` — dodaje 1 szt. rozmiaru `"36"` produktu `product`, składa zamówienie, sprawdza oba statusy 200.

- [ ] **Step 1: Testy frameworka (najpierw)** w `tests/framework/test_own_product.py`:

```python
def test_new_slug_is_unique_and_prefixed():
    a, b = new_slug(), new_slug()
    assert a != b
    assert a.startswith("test-")
    assert len(a) == 17


def test_product_row_defaults():
    row = product_row("test-abc")
    assert row["id"] == row["slug"] == "test-abc"
    assert row["amount"] == 200
    assert json.loads(row["stockBySize"]) == {"36": 5, "38": 5}
    assert json.loads(row["sizeCodes"]) == ["36", "38"]
    assert json.loads(row["unavailable"]) == []
    assert row["isPromo"] is False
    assert row["promoPercent"] == 0


def test_product_row_promo_and_empty_size():
    row = product_row("test-abc", stock={"36": 0, "38": 2}, promo_percent=20)
    assert row["isPromo"] is True
    assert row["promoPercent"] == 20
    assert json.loads(row["unavailable"]) == ["36"]


def test_own_product_price_applies_promo():
    assert OwnProduct("test-a", "n", 200, 20, {}).price == 160
    assert OwnProduct("test-a", "n", 200, 0, {}).price == 200


def test_delete_refuses_slug_without_test_prefix():
    class NoSql:
        def execute(self, *args, **kwargs):
            raise AssertionError("SQL nie może się wykonać")

    with pytest.raises(ValueError, match="zakiet-castello"):
        delete_product(NoSql(), "zakiet-castello")
```

- [ ] **Step 2:** Run: `uv run pytest tests/framework/test_own_product.py -q` → Expected: błąd importu.
- [ ] **Step 3:** Zaimplementuj `jersa.db.products` i `jersa.db.orders`.
- [ ] **Step 4:** Run: `uv run pytest tests/framework -q` → Expected: wszystkie zielone.
- [ ] **Step 5: Testy na bazie (najpierw)** w `tests/db/test_own_product_db.py`, wszystkie `regression`:
  - `test_product_row_covers_required_columns(db)`: z `information_schema.columns` pobierz kolumny `ProductRow` z `is_nullable = 'NO'` i `column_default IS NULL`; każda musi być kluczem `product_row("test-x")`. Komunikat asercji wymienia brakujące kolumny.
  - `test_own_product_is_visible_in_shop_and_removable(db, shop)`: `insert_product` (w `try/finally` z `delete_product`); `shop.search(slug)` zwraca dokładnie 1 produkt ze `slug`, `price.amount == 200`, rozmiary `36` i `38` z `available: true`; `shop.client.get(f"/produkt/{slug}")` → 200 i nazwa produktu w treści. Po `delete_product`: `SELECT count(*)` = 0 i `shop.search(slug)` → `[]`.
  - `test_delete_product_removes_its_orders_and_reviews(db, shop)`: wstaw produkt, dodaj do koszyka, złóż zamówienie, dodaj opinię; po `delete_product` w bazie nie ma zamówienia (po `id`), opinii (`productSlug`) ani produktu.
- [ ] **Step 6:** Zaimplementuj fixtures `make_product`, `product`, `placed_order`; dopisz moduły do `pytest_plugins`.
- [ ] **Step 7:** Run: `uv run pytest tests/db -q` → Expected: `4 passed`. Jeśli strona `/produkt/<slug>` nie zwraca 200 dla produktu wstawionego SQL-em, zatrzymaj się na ustaleniu przyczyny (systematic-debugging) — od tego zależy E2E w Task 9.
- [ ] **Step 8:** Run (bash): `DATABASE_URL= uv run pytest tests/db -q -rs` → Expected: testy pominięte z `DATABASE_URL nie jest ustawione`, zero błędów.
- [ ] **Step 9:** Commit: `Etap 3: własny produkt na test (fixtures, SQL, sprzątanie po ID)`.

### Task 4: Kontrakt

**Files:**
- Create: `schemas/cart.json`, `schemas/wishlist.json`, `schemas/reviews.json`, `schemas/order-created.json`, `schemas/payu-start.json`, `schemas/payu-notify.json`, `schemas/error.json`
- Create: `tests/contract/test_cart_contract.py`, `test_wishlist_contract.py`, `test_reviews_contract.py`, `test_checkout_contract.py`, `test_error_contract.py`
- Test: `tests/framework/test_project_schemas.py`

**Interfaces:**
- Consumes: `assert_matches_schema(body, "<nazwa pliku bez .json>")`, `shop`, `product`, `placed_order`.
- Produces: schematy z `$id` równym nazwie pliku, Draft 2020-12, `additionalProperties: false` na każdym obiekcie.

Kształty (spisz z realnej odpowiedzi, potem porównaj z tabelą; różnica = znalezisko do ledgera):

| Schemat | Kształt |
|---|---|
| `cart` | `{id: string, lines: [linia]}`; linia: wymagane `id, productSlug, size, quantity, product`; opcjonalne `customFit: boolean`, `sizeSurcharge: integer`; `quantity: integer`; `product`: `$ref product.json` albo `null` |
| `wishlist` | `{slugs: [string], products: [$ref product.json]}` |
| `reviews` | `{reviews: [{id, productSlug, author, body}]}`, same stringi, wszystkie wymagane |
| `order-created` | `{order: {id, publicToken}}`, oba stringi z wzorcem UUID |
| `payu-start` | `oneOf`: `{ok: const true, redirectUrl: string}` albo `{ok: const false, reason: string}` |
| `payu-notify` | `{ok: const true, duplicate: boolean}` |
| `error` | `{error: string, minLength 1}` |

- [ ] **Step 1: Test frameworka (najpierw)** `tests/framework/test_project_schemas.py`: parametryzowany po plikach `schemas/*.json`; każdy przechodzi `Draft202012Validator.check_schema`, ma `$id == <nazwa pliku>` i w pliku nie ma obiektu z `properties` bez `additionalProperties: false`. Run → Expected: `2 passed` (dwa istniejące pliki; po kroku 4 będzie 9).
- [ ] **Step 2: Testy kontraktu (najpierw)**, każdy `regression` + `contract`, asercja statusu, potem `assert_matches_schema`:

  | Test | Akcja | Schemat |
  |---|---|---|
  | `test_empty_cart_matches_contract` (K-02) | `shop.cart()` | `cart` |
  | `test_cart_with_line_matches_contract` (K-03) | `shop.add_to_cart(product.slug)`; `lines` niepuste, `lines[0].product` nie jest `null` | `cart` |
  | `test_wishlist_matches_contract` (K-04) | `shop.add_wish("zakiet-castello")`; `products` niepuste | `wishlist` |
  | `test_reviews_match_contract` (K-05) | `shop.reviews("zakiet-castello")`; `reviews` niepuste | `reviews` |
  | `test_order_created_matches_contract` (K-06) | koszyk z `product` + `shop.create_order()` | `order-created` |
  | `test_payment_start_matches_contract` (K-07) | `shop.start_payment(placed_order.id)`; `ok is True` | `payu-start` |
  | `test_payment_unavailable_matches_contract` (K-07) | `notify(id, "CANCELED")`, potem `start_payment`; `ok is False` | `payu-start` |
  | `test_payment_notify_matches_contract` (K-08) | `shop.notify(placed_order.id, "COMPLETED")` | `payu-notify` |
  | `test_error_matches_contract` (K-09) | `shop.add_to_cart(product.slug, size="")`; status 400 | `error` |

- [ ] **Step 3:** Run: `uv run pytest tests/contract -q` → Expected: nowe testy czerwone z `Brak schematu '…'`.
- [ ] **Step 4:** Napisz 7 schematów.
- [ ] **Step 5:** Run: `uv run pytest tests/contract tests/framework -q` → Expected: wszystkie zielone (kontrakt: 10).
- [ ] **Step 6: Kontrola czerwieni.** W `schemas/cart.json` usuń chwilowo `quantity` z `properties` linii. Run `uv run pytest tests/contract/test_cart_contract.py -q` → Expected: FAIL z `$.lines[0]: … 'quantity' was unexpected`. Przywróć plik.
- [ ] **Step 7:** Commit: `Etap 3: kontrakty koszyka, przechowalni, opinii, zamówienia, płatności i błędu`.

### Task 5: API — koszyk

**Files:** Create: `tests/api/test_cart.py`

**Interfaces:** Consumes: `shop`, `make_shop`, `product`, `MADE_TO_MEASURE`.

Wszystkie `regression`. Identyfikator pozycji bierz z odpowiedzi (`lines[0]["id"]`), nie składaj go ręcznie.

| Test | Akcja | Oczekiwany wynik |
|---|---|---|
| `test_add_product_creates_line` (A-CART-02, `smoke`) | `add_to_cart(product.slug, "36")` | 200; 1 pozycja: `productSlug`, `size == "36"`, `quantity == 1`, `customFit is False`, `product.slug == product.slug` |
| `test_same_product_and_size_increases_quantity` (03) | to samo dwa razy | 1 pozycja, `quantity == 2` |
| `test_two_sizes_make_two_lines` (04) | rozmiary `"36"` i `"38"` | 2 pozycje, rozmiary `{"36", "38"}` |
| `test_add_without_size_is_rejected` (05) | `size=""` | 400, `error == "Wybierz rozmiar"`; `cart().lines == []` |
| `test_add_without_product_is_rejected` (06) | `shop.client.post("/api/commerce/cart", json={"size": "36"})` | 400, `"Brak produktu"` |
| `test_made_to_measure_line` (07) | `add_to_cart(slug, MADE_TO_MEASURE, custom_fit=True)` | `size == "made-to-measure"`, `customFit is True`, `sizeSurcharge == 0` |
| `test_change_quantity` (08) | `set_quantity(line_id, 3)` | `quantity == 3` |
| `test_quantity_zero_removes_line` (09) | `set_quantity(line_id, 0)` | `lines == []` |
| `test_patch_without_required_field_is_rejected` (10) | parametry: `{"quantity": 2}`, `{"lineId": "x"}` | 400, `"Brak linii"` |
| `test_remove_line_keeps_other_lines` (11) | dwie pozycje, `remove_line` pierwszej | zostaje 1 pozycja, ta druga |
| `test_carts_are_separate_per_customer` (12) | `make_shop()` dwa razy; pierwszy dodaje produkt | drugi ma `lines == []` |
| `test_cart_survives_next_request` (13) | dodanie, potem `cart()` | ta sama pozycja i `id` koszyka |

- [ ] **Step 1:** Napisz testy z tabeli.
- [ ] **Step 2:** Run: `uv run pytest tests/api/test_cart.py -q` → Expected: `13 passed` (test 10 liczy się podwójnie).
- [ ] **Step 3: Kontrola czerwieni.** W `test_same_product_and_size_increases_quantity` zmień chwilowo oczekiwane `2` na `3` → Expected: FAIL z `assert 2 == 3`. Przywróć.
- [ ] **Step 4:** Commit: `Etap 3: testy API koszyka`.

### Task 6: API — zamówienie i płatność

**Files:** Create: `tests/api/test_orders.py`, `tests/api/test_payments.py`

**Interfaces:** Consumes: `shop`, `product`, `make_product`, `placed_order`, `SHIPPING`.

Zamówienie (`regression`):

| Test | Akcja | Oczekiwany wynik |
|---|---|---|
| `test_order_from_cart` (A-ORD-01, `smoke`) | koszyk z 1 szt., `create_order()` | 200; `order.id` i `order.publicToken` niepuste i różne; potem `cart().lines == []` |
| `test_order_from_empty_cart_is_rejected` (02) | `create_order()` bez koszyka | 400, `"Koszyk jest pusty"` |
| `test_order_without_email_is_rejected` (03) | `create_order(email="")` | 400, `"Brak e-maila"`; koszyk bez zmian |
| `test_order_without_shipping_field_is_rejected` (04) | parametry: każde z 5 pól `SHIPPING` po kolei puste | 400, `"Brak danych dostawy"`; koszyk bez zmian |
| `test_order_above_stock_is_rejected` (05) | `make_product(stock={"36": 1})`, `add_to_cart(quantity=2)` | 400, `"Brak stanu"`; koszyk nadal ma pozycję z `quantity == 2` |
| `test_second_order_from_same_cart_is_rejected` (06) | `placed_order`, potem `create_order()` | 400, `"Koszyk jest pusty"` |

Płatność (`regression`), każdy test na `placed_order`:

| Test | Akcja | Oczekiwany wynik |
|---|---|---|
| `test_start_payment_returns_payment_page` (A-PAY-01, `smoke`) | `start_payment(id)` | 200, `ok is True`, `redirectUrl == f"/preview/platnosc?order={id}"` |
| `test_start_payment_twice_returns_same_url` (02) | dwa razy | ten sam `redirectUrl` |
| `test_start_payment_for_unknown_order_is_rejected` (03) | `start_payment(str(uuid4()))` | 400, `"Nie znaleziono zamówienia"` |
| `test_start_payment_without_order_id_is_rejected` (04) | `shop.client.post("/api/commerce/payu/start", json={})` | 400, `"Brak zamówienia"` |
| `test_completed_payment_leads_to_order_page` (05, `smoke`) | `notify(id, "COMPLETED")`, `start_payment(id)` | notify: `{"ok": True, "duplicate": False}`; start: `redirectUrl == f"/zamowienie/{public_token}?paid=1"` |
| `test_second_completed_is_duplicate` (06) | `COMPLETED` dwa razy | drugie: `duplicate is True` |
| `test_canceled_payment_makes_order_unavailable` (07) | `notify(id, "CANCELED")`, `start_payment(id)` | start: `{"ok": False, "reason": "unavailable"}` |
| `test_pending_changes_nothing` (08) | `start_payment`, `notify(id, "PENDING")`, `start_payment` | notify: `duplicate is False`; oba `redirectUrl` równe adresowi strony płatności |
| `test_unknown_status_is_rejected` (09) | `notify(id, "REFUNDED")` | 400, `"Nieznany status"` |
| `test_completed_after_canceled_stays_canceled` (10) | `CANCELED`, potem `COMPLETED`, `start_payment` | `COMPLETED`: `duplicate is True`; start: `ok is False` |

- [ ] **Step 1:** Napisz testy z obu tabel.
- [ ] **Step 2:** Run: `uv run pytest tests/api/test_orders.py tests/api/test_payments.py -q` → Expected: `20 passed`.
- [ ] **Step 3: Kontrola czerwieni.** W `test_order_above_stock_is_rejected` zmień chwilowo stan na `{"36": 2}` → Expected: FAIL (status 200 zamiast 400). Przywróć.
- [ ] **Step 4:** Commit: `Etap 3: testy API zamówienia i płatności`.

### Task 7: API — opinie, przechowalnia, wyszukiwarka

**Files:** Create: `tests/api/test_reviews.py`, `tests/api/test_wishlist.py`, `tests/api/test_search.py`

**Interfaces:** Consumes: `shop`, `product`. Opinie dodawaj tylko do własnego produktu (sprząta je fixture). Przechowalnia i wyszukiwarka czytają seed.

| Test | Akcja | Oczekiwany wynik |
|---|---|---|
| `test_seed_reviews_are_listed` (A-REV-01) | `reviews("zakiet-castello")` | autorzy zawierają `"Paulina"` i `"Malwina"` |
| `test_added_review_is_listed` (02) | `add_review(product.slug, "Anna", "Leży świetnie.")`, potem `reviews` | 200; w obu odpowiedziach dokładnie 1 opinia z tym autorem i treścią |
| `test_review_without_author_is_rejected` (03) | `author=""` | 400, `"Podaj imię lub pseudonim"` |
| `test_review_without_body_is_rejected` (04) | `body=""` | 400, `"Napisz opinię"` |
| `test_reviews_without_product_are_rejected` (05) | `shop.client.get("/api/commerce/reviews")` | 400, `"Brak produktu"` |
| `test_review_for_unknown_product_is_rejected` (06) | `add_review("nie-ma-" + uuid4().hex, …)` | 400, `"Nie znaleziono produktu"` |
| `test_new_customer_has_empty_wishlist` (A-WISH-01) | `wishlist()` | `{"slugs": [], "products": []}`; ciasteczko `jersa_wish` |
| `test_add_to_wishlist` (02) | `add_wish("zakiet-castello")` | `slugs == ["zakiet-castello"]`; `products[0].slug` zgodny |
| `test_add_same_product_twice_keeps_one_entry` (03) | dwa razy | `slugs == ["zakiet-castello"]` |
| `test_remove_from_wishlist` (04) | `add_wish`, `remove_wish` | `{"slugs": [], "products": []}` |
| `test_wishlist_without_product_is_rejected` (05) | `shop.client.post("/api/commerce/wishlist", json={})` | 400, `"Brak produktu"` |
| `test_search_by_name_fragment` (A-SRCH-01) | `search("castello")` | slugi zawierają `"zakiet-castello"` |
| `test_search_ignores_case` (02) | `search("CASTELLO")` | te same slugi co dla `"castello"` |
| `test_search_by_slug_fragment` (03) | `search("zakiet-")` | slugi zawierają `"zakiet-castello"` |
| `test_empty_query_returns_nothing` (04) | `search("")` | `{"products": []}` |
| `test_query_without_matches_returns_nothing` (05) | `search(uuid4().hex)` | `{"products": []}` |

- [ ] **Step 1:** Napisz testy z tabeli (`regression`).
- [ ] **Step 2:** Run: `uv run pytest tests/api -q` → Expected: `50 passed` (1 + 13 + 20 + 16).
- [ ] **Step 3:** Commit: `Etap 3: testy API opinii, przechowalni i wyszukiwarki`.

### Task 8: Baza

**Files:** Create: `tests/db/test_orders_db.py`, `tests/db/test_payments_db.py`, `tests/db/test_reviews_db.py`

**Interfaces:** Consumes: `db`, `shop`, `product`, `make_product`, `placed_order`, `get_order`, `orders_of`, `read_stock`, `backdate_expiry`, `EMAIL`, `SHIPPING`, `MADE_TO_MEASURE`.

Wzorzec każdego testu: akcja przez API → odczyt SQL-em → porównanie ze stanem sprzed akcji. Stan sprzed akcji własnego produktu to `product.stock` (to, co wstawiła fixture). Wszystkie `regression`.

| Test | Akcja | Oczekiwany wynik w bazie |
|---|---|---|
| `test_order_row_matches_request` (D-ORD-01) | 2 szt. rozmiaru `"36"`, `create_order()` | `email == EMAIL`; `json.loads(shippingJson) == SHIPPING`; `linesJson`: 1 pozycja ze `productSlug`, `size "36"`, `quantity 2`, `customFit False`, `sizeSurcharge 0`; `total == product.price * 2`; `status == "awaiting_payment"`; `expiresAt - createdAt == timedelta(minutes=30)`; `payuOrderId is None` |
| `test_order_reserves_stock` (D-ORD-02) | to samo | `stock["36"] == product.stock["36"] - 2`; `stock["38"]` bez zmian |
| `test_made_to_measure_order_keeps_stock` (D-ORD-03) | `add_to_cart(slug, MADE_TO_MEASURE, custom_fit=True)`, zamówienie | `total == product.price + 100`; cały `stock` bez zmian |
| `test_promo_price_goes_into_total` (D-ORD-04) | `make_product(amount=200, promo_percent=20)`, 1 szt. | `total == 160` |
| `test_rejected_order_leaves_no_trace` (D-ORD-05) | `make_product(stock={"36": 1})`, `quantity=2`, `create_order()` → 400 | `orders_of(db, slug) == []`; `stock` bez zmian |
| `test_completed_payment_marks_order_paid` (D-PAY-01) | `placed_order`, `notify(COMPLETED)` | `status == "paid"`; `stock["36"] == product.stock["36"] - 1` (płatność nie zmienia stanu) |
| `test_canceled_payment_returns_stock` (D-PAY-02) | `placed_order`, `notify(CANCELED)` | `status == "cancelled"`; `stock == product.stock` (stan wrócił) |
| `test_expired_order_is_cancelled_and_restocked` (D-EXP-01) | `placed_order`, `backdate_expiry`, `start_payment(id)` | odpowiedź `{"ok": False, "reason": "unavailable"}`; `status == "cancelled"`; `stock == product.stock` (stan wrócił) |
| `test_review_is_stored_trimmed` (D-REV-01) | `add_review(product.slug, "  Anna  ", "  Leży świetnie.  ")` | 1 wiersz `ReviewRow` dla sluga: `author == "Anna"`, `body == "Leży świetnie."` |

- [ ] **Step 1:** Napisz testy z tabeli.
- [ ] **Step 2:** Run: `uv run pytest tests/db -q` → Expected: `13 passed`.
- [ ] **Step 3: Kontrola czerwieni.** W `test_order_reserves_stock` zmień chwilowo oczekiwaną różnicę z 2 na 1 → Expected: FAIL z obiema wartościami w komunikacie. Przywróć.
- [ ] **Step 4:** Commit: `Etap 3: testy bazy dla zamówień, płatności i opinii`.

### Task 9: E2E

**Files:**
- Modify: `src/jersa/pages/product_page.py`
- Create: `src/jersa/pages/checkout_page.py`, `src/jersa/pages/order_page.py`, `src/jersa/pages/search_page.py`, `src/jersa/pages/wishlist_page.py`
- Create: `tests/e2e/test_purchase.py`, `tests/e2e/test_cart_e2e.py`, `tests/e2e/test_search_e2e.py`, `tests/e2e/test_wishlist_e2e.py`

**Interfaces:**
- Consumes: fixture `page` (pytest-playwright, `base_url` z konfiguracji), `product`, `db`, `shop`, `order_id_by_token`, `EMAIL`, `SHIPPING`.
- Produces (page objecty; selektory po roli i etykiecie, potwierdzone w testach E2E sklepu):

  | Klasa | Metody i lokatory |
  |---|---|
  | `ProductPage` | `open(slug)`; `heading`; `choose_size(code)` → przycisk o nazwie `code` (dokładnie); `add_to_cart()` → przycisk `/Do koszyka/i`; `cart_drawer` → `dialog` o nazwie `Koszyk`; `go_to_checkout()` → w szufladzie link `/Płacę/i`; `size_alert` → `alert` z tekstem `Wybierz rozmiar albo dopasowanie do wymiarów klientki`; `add_to_wishlist()` → przycisk `Dodaj do ulubionych`, czeka na odpowiedź `POST /api/commerce/wishlist` |
  | `CheckoutPage` | `fill(email, shipping)` → pola po etykietach `/e-mail/i`, `/Imię/i`, `/Ulica/i`, `/Miasto/i`, `/Kod/i`, `/Telefon/i`; `submit()` → przycisk `/Zamawiam/i` |
  | `OrderPage` | `token` → ostatni segment ścieżki URL `/zamowienie/<token>`; `status(text)` → lokator tekstu |
  | `SearchPage` | `open(q)` → `/szukaj?q=<q>`; `result(name)` → link o nazwie zawierającej `name` |
  | `WishlistPage` | `open()` → `/ulubione`; `heading` → nagłówek `/Ulubione/i`; `item(name)` → link |

Testy (`regression`):

| Test | Kroki | Oczekiwany wynik |
|---|---|---|
| `test_guest_buys_product` (E-01, `smoke`) | strona własnego produktu → rozmiar `36` → do koszyka → szuflada → „Płacę” → kasa: `EMAIL` i `SHIPPING` → „Zamawiam” | URL `/zamowienie/…`; widać `Oczekuje na płatność` i sumę `200,00 zł`. Potem `shop.notify(order_id_by_token(db, token), "COMPLETED")`, `page.reload()` → widać `Opłacone` |
| `test_size_is_required` (E-02) | strona `zakiet-castello` → „Do koszyka” bez rozmiaru | widać `size_alert`; `page.request.get("/api/commerce/cart")` → `lines == []` |
| `test_search_leads_to_product` (E-03) | `SearchPage.open("castello")` → klik w „Żakiet CASTELLO” | URL kończy się `/produkt/zakiet-castello`; nagłówek `Żakiet CASTELLO` |
| `test_heart_adds_to_wishlist` (E-04) | strona `zakiet-castello` → serduszko → `/ulubione` | nagłówek „Ulubione”; link „Żakiet CASTELLO” widoczny |

Płatność w E-01 idzie przez API, bo przycisk symulacji pojawi się w sklepie później (spec, decyzja 6). Komentarz w teście ma to mówić jednym zdaniem, bez opisu stanu sklepu.

- [ ] **Step 1:** Napisz page objecty i testy.
- [ ] **Step 2:** Run: `uv run pytest tests/e2e -q` → Expected: `5 passed`. Przy porażce: `--headed --slowmo 300` albo `--tracing retain-on-failure`.
- [ ] **Step 3: Kontrola czerwieni.** W `test_guest_buys_product` zmień chwilowo oczekiwaną sumę na `201,00 zł` → Expected: FAIL z komunikatem Playwrighta o tekście. Przywróć.
- [ ] **Step 4:** Commit: `Etap 3: page objecty i testy E2E zakupu, wyszukiwania i przechowalni`.

### Task 10: Powtarzalność i dokumentacja

**Files:** Modify: `KNOWLEDGE.md`, `CLAUDE.md`, `README.md`, `docs/api-reference.md`

- [ ] **Step 1: Trzy przebiegi bez restartu.** Zapisz stan seeda: `SELECT md5(string_agg("stockBySize", '|' ORDER BY slug)) FROM "ProductRow" WHERE slug NOT LIKE 'test-%'`. Uruchom trzy razy `uv run pytest -q`. Expected: trzy razy `131 passed` (framework 53, kontrakt 10, API 50, baza 13, E2E 5; jeśli liczba jest inna, uzgodnij ją z tabelami zadań i zapisz w ledgerze), ten sam md5 po każdym przebiegu.
- [ ] **Step 2: Brak śladów.** Expected `0` w każdym: `SELECT count(*) FROM "ProductRow" WHERE slug LIKE 'test-%'`; `SELECT count(*) FROM "OrderRow" WHERE "linesJson" LIKE '%"productSlug":"test-%'`; `SELECT count(*) FROM "ReviewRow" WHERE "productSlug" LIKE 'test-%'`.
- [ ] **Step 3: Dowolna kolejność i markery.** Run: `uv run pytest -q tests/e2e tests/db tests/api tests/contract` (odwrócona kolejność katalogów) → wszystkie zielone. Run: `uv run pytest -m smoke -q` → Expected: `9 passed`.
- [ ] **Step 4: Macierz śledzenia.** W `docs/traceability.json` ustaw `status` wszystkich wykonanych przypadków na `zautomatyzowany` i `updated` na datę wykonania. Run: `uv run pytest tests/framework/test_traceability.py -q` → Expected: zielone (test sprawdza, że każda funkcja z pola `tests` istnieje w kodzie). Run: `uv run python scripts/build_traceability.py` → Expected: `Zapisano docs	raceability-matrix.pdf`; w PDF „zaplanowane: 0”.
- [ ] **Step 5: `KNOWLEDGE.md`.**
  - Sekcja 4: ADR-012 „Własny produkt na test” (zamyka wiersz „Strategia stanu magazynowego” w otwartych decyzjach; alternatywy i koszt ze spec, decyzja 4), ADR-013 „Oczekiwany wynik z reguł biznesowych, asercje względem stanu sprzed akcji” (spec, decyzje 2 i 3), ADR-014 „Testy dla zachowań czekających na zmianę w sklepie nie trafiają do publicznego repo przed tą zmianą” (spec, decyzja 1; bez wymieniania zachowań). Każdy z wypełnionym polem „Na rozmowie”: 1–3 proste zdania.
  - Sekcja 9, pytania z odpowiedzią i dowodem w projekcie: „Skąd wiesz, że dane naprawdę zapisały się w bazie?”, „Jak przygotowujesz dane testowe i jak po sobie sprzątasz?” (fixture z `yield`, fabryka), „Dlaczego test nie zakłada stałych wartości z seeda?”, „Jak testujesz coś, co zależy od czasu (wygasanie zamówienia)?”, „Co to jest idempotencja i jak ją testujesz?”, „Skąd bierzesz scenariusze testowe?”, „Do czego służy macierz śledzenia wymagań (traceability matrix)?”, „Do czego służy `parametrize`?”, „Dlaczego klient API nie rzuca wyjątku na błąd 400?”.
  - Sekcja 2: notatki Etapu 3 (krok A zrobiony, krok B (kolejne testy API) czeka na zmianę w sklepie; Etap 4 = równoległość). Sekcja 6: problemy rozwiązane po drodze (z ledgera). Sekcja 8: kroki, po jednym zdaniu.
- [ ] **Step 6:** `docs/api-reference.md`: dopisz `DELETE /api/commerce/wishlist` (body `{productSlug}`, odpowiedź jak `GET`) do tabeli i sekcji; w danych testowych dopisz, że produkty seeda mają `promoPercent` 0. `README.md`: link do `docs/traceability-matrix.pdf`, liczby testów i polecenia (`-m smoke`, `-m regression`, pojedynczy poziom). `CLAUDE.md`: struktura (`clients/commerce.py`, `db/products.py`, `db/orders.py`), konwencja „własny produkt na test”, status etapu.
- [ ] **Step 7:** Run: `uv run ruff check && uv run ruff format --check && uv run pytest tests/framework -q` → Expected: bez uwag, `53 passed`.
- [ ] **Step 8:** Commit: `Etap 3: dokumentacja kroku A (ADR-012…014, pytania, referencja API)`.
