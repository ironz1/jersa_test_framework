# Kasa, krok 2: testy kasy, kodów rabatowych i płatności — projekt

Data: 2026-11-19. Rozmiar: projekt. Gałąź: `kasa-krok-2` od `main` repo testów (sklep z kasą jest już na `main`, para gałęzi niepotrzebna).

## Po co

Kasa sklepu (`/kasa`, kody rabatowe, dostawy, PayU) jest na `main` sklepu i na Vercelu. Krok 1 tylko dopasował stare testy. Nowe zachowania (walidacja kasy, rabaty, cena dostawy, odpis zamówienia, kwota w powiadomieniu PayU, panel kodów) nie mają testów, więc bramka na PR sklepu ich nie pilnuje. Krok 2 je dodaje. Cel portfolio: pokazać testy logiki pieniędzy (rabat, zaokrąglenie, grosze) na trzech poziomach i dane testowe izolowane przy 4 procesach.

Źródło prawdy: spec sklepu `docs/superpowers/specs/2026-11-17-kasa-payu-design.md` (z poprawką `eba7b3d`: odpowiedź zamówienia zostaje `{ order: { id, publicToken } }`) oraz zachowanie kodu na `main` sklepu.

## Podejścia (skąd testy biorą kody rabatowe)

- **A. Fixture wstawia kod do bazy** (wybrane przez właściciela 2026-11-19). `make_discount_code(...)` jak `make_product`: własny kod na test, sprzątanie po ID. Testy kasy nie zależą od panelu admina, datę końca da się ustawić dokładnie. Panel admina sprawdzają osobne testy z logowaniem przez formularz w przeglądarce.
- **B. API admina z ciasteczkiem wyliczonym w teście (HMAC hasła).** Odrzucone: test znałby wewnętrzny sposób liczenia tokenu, zmiana w sklepie psułaby wszystkie testy kodów.
- **C. Wszystko przez API admina po logowaniu w przeglądarce.** Odrzucone: wolniej, a błąd panelu zatrzymywałby testy rabatów w kasie.

## Cele, anty-cele

- **Cele:** każde wymaganie kasy z listy poniżej ma test na najniższym poziomie, który je pokazuje; testy niezależne przy `-n 4`; pełny zestaw zielony na `main` sklepu; jeden nowy E2E.
- **Anty-cele:** testy zależne od seeda albo od kodów innych testów; test, który woła prawdziwe PayU; czekanie na maila; liczby z seeda na sztywno (ADR-013).
- **Poza zakresem:** podpis powiadomienia PayU (wymaga kluczy żywego sandboxa; w Dockerze jest mock), wysyłka maila (bez klucza Resend tylko log), wygasanie po 30 minutach (już R4), strona `/admin` w przeglądarce poza logowaniem.

## Dane testowe (nowe elementy frameworka)

- **`make_discount_code(kind="percent"|"amount", value=..., ends_on=None|date, active=True)`** w `src/jersa/fixtures/`: wstawia wiersz do `"DiscountCode"` z kodem `test-<hex>` (zawsze z prefiksem testowym, więc nie koliduje z kodami operatora ani innych testów), zwraca obiekt z `id`, `code`, `kind`, `value`. Teardown usuwa **po ID** swoje wiersze. SQL w `src/jersa/db/discount_codes.py`. `endsOn` zapisywany jako północ UTC tej daty (tak czyta go sklep: `toISOString().slice(0, 10)`).
- **„Dziś” w Warszawie** liczy test, nie sklep: `datetime.now(ZoneInfo("Europe/Warsaw")).date()` (strefa działa w środowisku `uv`, sprawdzone 2026-11-19). Test daty granicznej: kod z końcem „dziś” działa, z końcem „wczoraj” nie.
- **`CommerceApi`** dostaje metody: `apply_discount(code)` (`POST /api/commerce/discount`) i `checkout_order(checkout: dict)` (`POST /api/commerce/orders` z polem `checkout`). `notify(...)` dostaje opcjonalny `total_amount` (grosze, jako tekst jak w PayU).
- **Dane kasy:** `checkout_body(**overrides)` buduje pełne poprawne pole `checkout` z `BUYER` (z kroku 1) + `email`, `buyerKind: "private"`, `country: "Polska"`, `termsAccepted: True`, `shippingMethodId: "kurier-dpd"`, puste pola firmy, drugiego adresu i uwag. Test nadpisuje tylko to, co sprawdza.
- **Admin:** fixture `admin` (zakres sesji procesu) loguje się przez formularz `/admin/login` w Playwright, przenosi ciasteczko `jersa_admin` do sesji `requests` i zwraca klienta `AdminApi` (`codes()`, `create_code(...)`, `disable_code(id)`). Hasło z `Settings.admin_password`; gdy go nie ma w `.env` ani w zmiennych, domyślnie `dev-admin`, czyli ta sama wartość domyślna, której używa `docker-compose.yml` (dzięki temu bramka w repo sklepu działa bez zmiany jej workflow). Kody utworzone przez panel w testach też mają prefiks `test-<hex>` i są sprzątane po ID z odpowiedzi przez SQL (panel umie tylko wyłączyć kod, nie usunąć). Dlatego `admin` zależy od `db` i bez `DATABASE_URL` jest pomijany, tak jak `make_product` i `make_discount_code` (decyzja wykonawcy-projektanta: na STG bez bazy testy kodów i panelu są pomijane, jak dziś wszystkie testy z własnym produktem).

## Przypadki (wymaganie → poziom)

Nowe wymagania w macierzy (źródło: spec kasy sklepu, rozdział w nawiasie). Numeracja od R27.

**Kody rabatowe na koszyku** (`/api/commerce/discount`), poziom API:
- Rabat procentowy = `round(podstawa × procent / 100)`, kwotowy = `min(wartość, podstawa)`; podstawa to produkty po cenie sprzedaży (promocja, dopłata za miarę), bez dostawy (rozdz. 3). Koszyk pokazuje `discountCode` i `discountAmount`. Przypadek zaokrąglenia: podstawa i procent dobrane tak, żeby wynik miał ,5 (np. 25 zł × 10%).
- Wielkość liter ignorowana; koszyk pokazuje pisownię operatora (rozdz. 3).
- Kod nieznany, wyłączony albo po dacie, wpisany do koszyka **bez kodu**: 400 „Kod jest nieprawidłowy”, koszyk bez rabatu (rozdz. 2, 8). Zły kod wpisany do koszyka, który ma już dobry kod: 400, poprzedni kod i rabat zostają (decyzja właściciela niżej).
- Data końca włącznie (dziś działa, wczoraj nie) według Europe/Warsaw; kod bez daty działa (rozdz. 3).
- Puste pole zdejmuje kod; nowy kod zastępuje poprzedni; jeden kod na koszyk (rozdz. 2).

**Kasa** (`POST /api/commerce/orders` z `checkout`), poziomy API i Baza:
- Poprawna kasa: 200, odpowiedź `{ order: { id, publicToken } }` (kontrakt jak K-06); suma w bazie = produkty − rabat + dostawa (rozdz. 3). Każda z trzech metod dostawy ma swoją cenę (0, 14, 15 zł).
- Cena dostawy z listy sklepu: pole ceny wysłane przez klienta jest ignorowane (rozdz. 3).
- Walidacja z komunikatem (rozdz. 8): każde wymagane pole osobno (parametryzacja: imię, nazwisko, e-mail, telefon, ulica, kod pocztowy, miasto), brak regulaminu, brak albo nieznana dostawa, firma bez nazwy, zły NIP, kraj inny niż Polska (adres rozliczeniowy i drugi adres), drugi adres zaznaczony bez pól. Po odrzuceniu koszyk zostaje, zamówienia w bazie nie ma.
- NIP ze spacjami i myślnikami zapisany jako 10 cyfr (rozdz. 3).
- Kod na koszyku, który przestał działać przed złożeniem zamówienia (wyłączony): 400 „Kod jest nieprawidłowy”, brak zamówienia, kod zdjęty z koszyka, produkty zostają (rozdz. 3, 8).
- Baza: odpis `checkoutJson` (kupująca, rodzaj, adres rozliczeniowy, uwagi, regulamin, id, nazwa i cena dostawy, kod i kwota rabatu); `shippingJson` to drugi adres, gdy był zaznaczony, w przeciwnym razie adres z formularza (rozdz. 4); `email` zamówienia to e-mail z formularza. Odpis nie zmienia się po późniejszym wyłączeniu kodu (rozdz. 5).

**Płatność** (`/api/commerce/payu/notify`, tryb mock), poziom API:
- Powiadomienie z kwotą w groszach równą sumie (z rabatem i dostawą) oznacza opłacone (rozdz. 6).
- Inna kwota: 400 „Kwota nie zgadza się z zamówieniem”, status bez zmian (rozdz. 6, 8).

**Panel kodów** (`/api/admin/discount-codes`), poziomy API i Kontrakt:
- Bez logowania: 401 „Brak dostępu”.
- Utworzenie (procent, kwota, z datą i bez), lista zawiera kod; wyłączenie sprawia, że kod nie działa w koszyku (rozdz. 5).
- Walidacja: pusty kod, rodzaj spoza dwóch, wartość < 1, procent > 100, zła data, duplikat bez względu na wielkość liter („Taki kod już istnieje”).

**Kontrakt:** nowe schematy dla odpowiedzi `POST /api/commerce/discount` (`{ ok, discount }`) i panelu kodów (lista i utworzony kod); błędy przez istniejący `error.json`.

**E2E** (jeden): gość dodaje produkt, na `/koszyk` wpisuje kod i klika Zastosuj, w `/kasa` wybiera dostawę, składa zamówienie; strona zamówienia pokazuje sumę z rabatem i dostawą. Page object `/koszyk` dostaje pole kodu.

## Zasady wykonania

- Każdy test: marker `regression`; `smoke` dostaje poprawna kasa przez API bez kodu (ścieżka krytyczna; E2E z kodem tylko `regression`, żeby smoke po deployu nie zależał od panelu kodów), docstring zaczyna się od ID, wpis w `docs/traceability.json`, nowe wymagania R27+.
- Własny produkt na każdy test, który coś kupuje albo liczy rabat (`make_product` z ceną dobraną do przypadku); seed tylko czytany.
- Stary kształt zamówienia (`email` + `shipping`) zostaje w istniejących testach, dopóki sklep go obsługuje; nowe testy używają `checkout`.
- **ADR-014:** jeśli nowy test pokaże zachowanie niezgodne ze spec, test nie trafia do publicznego repo. Opis z odtworzeniem idzie do agenta sklepu (lokalny handoff wykluczony z gita), a test czeka na poprawkę.

## Decyzja właściciela

- **Zły kod na koszyku z dobrym kodem.** Spec (rozdz. 2): „Zły, wyłączony albo przeterminowany kod zostawia koszyk bez rabatu”. Kod `main` sklepu (`applyDiscount`) przy złym kodzie zwraca 400 i **zostawia** wcześniejszy dobry kod z rabatem. **Decyzja właściciela 2026-11-19:** obowiązuje zachowanie sklepu, poprzedni kod zostaje (klientka, która pomyli się przy drugim kodzie, nie traci rabatu). Test: koszyk z dobrym kodem, zły kod → 400 „Kod jest nieprawidłowy”, koszyk nadal z poprzednim kodem i rabatem. Wymaganie w macierzy z tym źródłem.

## Co zostaje wykonawcy

Dokładne nazwy przypadków i ich ID (`K-10…`, `A-DISC-…`, `A-CHK-…`, `A-PAY-…`, `A-ADM-…`, `D-CHK-…`, `E-04`), podział na pliki testów, ceny własnych produktów dla przypadków zaokrąglenia, lokator pola kodu na `/koszyk`, sposób odczytu „wczoraj/dziś” w teście.
