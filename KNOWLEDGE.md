# jersa_test_framework — baza wiedzy

> Dziennik wiedzy z budowy frameworka testowego.
> Dwa cele: **materiał na rozmowy rekrutacyjne (SDET)** oraz **mapa do budowania kolejnych frameworków**.
>
> Zasada zapisu: przy każdej decyzji i praktyce zapisuję nie tylko *co*, ale przede wszystkim *dlaczego*.

---

## 1. Cel i zakres

- **Cel:** kompletny framework testowy na własnym sklepie jako portfolio SDET (Python, Playwright, API, GitHub Actions, AWS).
- **System testowany:** jersa-storefront (`ironz1/jersa-storefront`, branch `main`)
  - Frontend: Next.js 16 (App Router), React 19, TypeScript, Tailwind 4, Motion
  - API: BFF w Route Handlers — `/api/commerce/*` (koszyk, wishlist, wyszukiwarka, opinie, zamówienia, płatność PayU) i `/api/admin/*` (po zalogowaniu). Brak OpenAPI.
  - Baza: Prisma 6 — SQLite lokalnie, Neon Postgres na Vercelu
  - Hosting: Vercel Hobby; płatności PayU (na razie mock)
  - Istniejące testy: Vitest (65 jednostkowych), Playwright w TS (koszyk, kasa, admin)
- **Stack frameworka:** Python 3.12 (uv), pytest, Playwright, requests, psycopg 3, jsonschema, pydantic-settings, ruff; później pytest-xdist (Etap 4) i narzędzie raportów (Etap 5)
- **Cele nauki:** testy na wielu poziomach, Docker, CI/CD (GitHub Actions), AWS
- **Poza zakresem (na teraz):** zmiany architektury sklepu, Pact, wydzielony backend (Etap 8), Azure DevOps / GitLab CI

### Poziomy testów

| Poziom | Narzędzie | Co sprawdza |
|---|---|---|
| Jednostkowe (istnieją) | Vitest | Logikę w izolacji |
| Kontraktu | jsonschema | Kształt odpowiedzi API: pola, typy, błędy |
| API | pytest, requests | Endpointy, statusy, błędy, autoryzację admina |
| Weryfikacja bazy | psycopg 3, SQL | Stan bazy po wywołaniach API, integralność |
| E2E | Playwright (Python) | Kluczowe przepływy (koszyk, kasa) |

Zasada: im wyżej w piramidzie, tym mniej scenariuszy. Markery `smoke`, `regression`, `contract` przecinają poziomy.

---

## 2. Mapa procesu (etapy wdrożenia)

Każdy etap: co zrobiłem → czego się nauczyłem → linki do ADR / praktyk.

- [x] **Etap 0 — Przygotowanie (~0,5 dnia):** przełączanie Prismy SQLite ↔ Postgres, lista endpointów i przykładowych odpowiedzi, seed danych
- [x] **Etap 1 — Sklep w Dockerze (1–2 dni):** Dockerfile multi-stage (standalone), docker-compose: app + postgres, healthchecki, migracje i seed
- [x] **Etap 2 — Szkielet repo testów (~1 dzień):** struktura, `conftest.py` (base_url, api_client, db_conn, page, assert_matches_schema), markery, ruff
- [x] **Etap 3 — Warstwy testów (3–5 dni):** kontrakt, API, DB, E2E. **Krok A zrobiony 2026-11-13:** 83 testy sklepu dla zachowań, które sklep ma poprawnie. **Krok B** (kolejne testy API) wydzielony poza etap: czeka na zmianę w sklepie i wróci jako osobna praca
- [x] **Etap 4 — Równoległość (~1 dzień), 2026-11-16:** pytest-xdist, `-n 4` domyślnie (ADR-015). Własne dane testu i sprzątanie po ID zrobione już w Etapie 3 (ADR-012)
- [ ] **Etap 5 — CI (1–2 dni): 5A zrobione 2026-11-17 (bramka na PR sklepu, informacyjna na darmowym planie, ADR-016); zostaje 5B.** Bramka na PR sklepu (główny trigger), push/PR w repo testów, nightly regression, smoke po deployu, raporty i trace jako artefakty — patrz ADR-005
- [ ] **Etap 6 — AWS (3–5 dni, osobno):** budżet i alerty, ECR (OIDC), RDS, App Runner + VPC connector
- [ ] **Etap 7 — Dokumentacja (0,5–1 dnia):** README w obu repo, diagram, jak dodać schemat i test
- [ ] **Etap 8 — (opcjonalny) Wydzielenie backendu:** osobne repo, OpenAPI, ewentualnie Pact

Priorytet: etapy 0–5 dają kompletne portfolio bez kosztów AWS.

### Notatki z etapów

### Etap 0 — 2026-10-27 → 2026-10-27

**Prisma: SQLite ↔ Postgres**
- `DATABASE_URL` wybiera bazę, ale provider w commitowanym `prisma/schema.prisma` jest zawsze `sqlite` — sam URL Postgresa nie wystarczy (Prisma padnie na niezgodności providera).
- Przełącznik jest dwuetapowy:
  1. **Silnik sklepu** (`src/lib/commerce-mode.ts`): `COMMERCE=own` → OwnCommerce; `COMMERCE=mock` → MockCommerce (nawet przy Postgresie); bez `COMMERCE`, ale z URL `postgres://` / `postgresql://` (`DATABASE_URL`, `POSTGRES_PRISMA_URL` lub `POSTGRES_URL`) → OwnCommerce.
  2. **Provider Prismy** (`scripts/prepare-database.mjs`, odpalany w `npm run build`): URL nie-Postgres → zostaje SQLite; URL Postgres → kopia schematu z `provider = "postgresql"` do gitignore'owanego `prisma/schema.postgres.prisma` → `prisma generate` → `db push` → `seed-catalog.ts`.
- `db push` i seed idą na URL bezpośredni: `DATABASE_URL_UNPOOLED` lub `POSTGRES_URL_NON_POOLING`, w przeciwnym razie `DATABASE_URL`.
- **Brak `prisma/migrations`** — schemat przez `db push`, nie `migrate`.
- Pułapka: lokalny `file:./prisma/dev.db` ląduje w `prisma/prisma/dev.db` (ścieżka względem katalogu schematu).

**Konfiguracja dla Dockera / pytest**
```
COMMERCE=own
DATABASE_URL=postgresql://jersa:jersa@postgres:5432/jersa
```
To samo co na Vercelu: `node scripts/prepare-database.mjs` (rewrite providera + `db push` + seed). W Etapie 1 robi to usługa `db-init`, nie entrypoint.

**Granice kontraktu API**
- Katalog (home, PDP, kategorie) to React Server Components — **brak REST GET produktu**. Kontrakt API obejmuje tylko BFF `/api/commerce/*`; katalog testujemy przez E2E.
- Ciasteczka (httpOnly, `path=/`, `SameSite=Lax`):

  | Cookie | Rola |
  |---|---|
  | `jersa_cart` | UUID koszyka, tworzone przy pierwszym GET/POST cart |
  | `jersa_wish` | UUID przechowalni (wishlist) |

- Błędy: `{ "error": "<polski string>" }`, status 400 (409 tylko przy admin slug) — jeden wspólny schemat błędu.

**Endpointy i seed** — pełna referencja z przykładami: [`docs/api-reference.md`](docs/api-reference.md).
- 12 endpointów BFF: koszyk (GET/POST/PATCH/DELETE), wishlist (GET/POST), search, reviews (GET/POST), orders, payu/start, payu/notify.
- Seed: 5 produktów, **5 szt. na rozmiar**; stabilny happy path = CASTELLO rozmiar 36.

**Wnioski dla frameworka**
- **Izolacja przez sesję:** koszyk i wishlist są per ciasteczko → świeży klient HTTP (nowa sesja) na test daje izolację za darmo.
- **Stan magazynowy to zasób współdzielony:** każde zamówienie zdejmuje stan; przy 5 szt. równoległe testy na CASTELLO 36 wyczerpią go po 5 zamówieniach → teardown musi przywracać stan (SQL) albo testy muszą rozkładać się na różne rozmiary.
- **Opinie nie mają DELETE:** teardown przez SQL; autor z prefiksem uuid, żeby sprzątać tylko swoje.
- **Kontrakt:** `Product` powtarza się w cart, wishlist i search → jedna definicja współdzielona (`$ref`); `customFit` i `sizeSurcharge` opcjonalne; jeden schemat błędu.
- **PayU mock bez podpisu:** można testować idempotencję (`payu/start` ten sam redirect, drugi `COMPLETED` → `duplicate: true`) i przejścia statusów.

**Implikacje dla Etapu 1 (Docker), wstępne z Etapu 0; entrypoint zastąpiła usługa `db-init`, patrz notatki Etapu 1**
- W sklepie nie ma `output: "standalone"` ani Dockerfile → trzeba dodać `output: "standalone"` w `next.config.ts`.
- Multi-stage: deps → build. `prepare-database` przy buildzie wymaga Postgresa → push i seed przenieść do entrypointu.
- Compose: `postgres:16` + app z `COMMERCE=own` i `DATABASE_URL=postgresql://...`.
- Entrypoint: `node scripts/prepare-database.mjs`, potem `node server.js` (standalone).
- Healthchecki: db → `pg_isready`; app → `GET /api/commerce/search?q=castello`, aż wróci CASTELLO (dowód, że seed przeszedł).
- Obraz musi powtarzać generate + push + seed przy starcie (Vercel robi to w buildzie), bo commitowany schemat to SQLite.

### Etap 1 — 2026-11-01 → 2026-11-06

**Ustalenia z repo sklepu (odczyt przez `gh`, 2026-11-01)**
- `npm run build` = `prepare-database.mjs && next build` → na Vercelu baza jest przygotowywana **w buildzie**. W `docker build` bazy nie ma, a skrypt bez URL Postgres kończy się po cichu → klient Prismy zostałby pod SQLite. Potrzebny tryb `--generate-only`.
- `prisma` i `tsx` są w `devDependencies` → nie ma ich w obrazie standalone. Dlatego przygotowanie bazy w osobnej usłudze `db-init` (etap `builder`), a nie w entrypoincie aplikacji.
- Standalone nie kopiuje `public/` ani `.next/static` — trzeba ręcznie.
- Stan magazynowy: kolumna `ProductRow.stockBySize` (JSON) per produkt → test może wstawić własny produkt z własnym stanem.
- Potwierdzone 2026-11-04: `next build` bez bazy pada na `/blog` (Prisma bez `try/catch`), a `/szycie-na-miare` zostawałaby na stałe z danymi z mocka. Rozwiązanie: ADR-007, zadanie dla Groka: [`docs/handoff/2026-11-05-etap-1-docker-fix.md`](docs/handoff/2026-11-05-etap-1-docker-fix.md).
- Seed nie zawierał wpisów bloga. Od `5e94298` (2026-11-05) tworzy jeden: `kombinezon-zamiast-sukienki` (id `blog-kombinezon`). Testy bloga, które coś zmieniają, i tak tworzą własny wpis (Etap 3).
- `jersa-storefront.vercel.app` to piaskownica bez ruchu → traktujemy jako **STG**; właściwy sklep będzie na osobnym środowisku (PROD). Push na `main` sklepu deployuje od razu (brak PR-ów).
- Agent sklepu (Grok) czyta `AGENTS.md` → `CLAUDE.md`; zasady „nie pushuj bez polecenia”, decyzje w `CLAUDE.md` + `docs/PLAN.md`.

**Wynik lokalny (2026-11-05, czysta kopia commita `4021449`, bez niezacommitowanych stron: `/faq` zwraca 404)**
- `docker compose up -d --build --wait` kończy się sukcesem: `postgres` i `app` healthy, `db-init` exited (0). Build z cache zależności trwa ok. 67 s (czasu pierwszego pełnego builda nie zmierzono), kolejny start z gotowych obrazów ok. 13 s.
- Obrazy: `runner` 380 MB, `builder` 1,28 GB, `postgres:16` 451 MB. Na dysku ok. 2 GB obrazów (wspólne warstwy) i ok. 1,3 GB cache budowania (zmierzone na obrazie z folderu).
- `search?q=castello` zwraca `zakiet-castello` (350 zł); strona główna, PDP, zdjęcie produktu z `public/`, plik z `/_next/static` i logo przez `/_next/image` odpowiadają 200. Tabela tras z `next build` oznacza `/blog` i `/szycie-na-miare` jako dynamiczne (`ƒ`).
- Baza: 5 produktów, po 5 szt. na rozmiar, 0 wpisów bloga.
- **Strony czytają Postgresa, nie mocka:** znacznik wstawiony w SQL widać na `/szycie-na-miare`, `/produkt/suknia-mandisa`, `/blog` i `/blog/<slug>`.
- `down -v` + `up` przywraca seed (zmieniony stan i nazwa wracają, blog znów pusty); `down` + `up` bez `-v` też przechodzi.
- Pierwsze sprawdzenie przeszło na obrazie z folderu (z niezacommitowanymi stronami), dlatego powtórzone na eksporcie `git archive` samego commita.
- `tsc` bez błędów. Vitest: 74/74 według Groka; u mnie 44 zielone i 30 pominiętych przez blokadę Prismy (sekcja 6).
- Nie sprawdzono jeszcze ścieżki Vercela (`npm run build` z Postgresem): potwierdzi ją deploy.
- **Porty (2026-11-05):** sklep w Dockerze jest na hoście na `127.0.0.1:3100` (w kontenerze nadal 3000), bo `next dev` i Playwright sklepu używają 3000. Bez rozdzielenia ich przeglądarka trafiałaby w kontener ze starym kodem. Port rozdziela tylko uruchomienie: `--build` nadal bierze kod z folderu, w którym pracuje agent sklepu; stabilną wersję daje `STOREFRONT_PATH` wskazujący eksport commita.

**Zamknięcie (2026-11-06, sklep `91b5669` wypchnięty, folder sklepu = `origin/main`, bez niezacommitowanych zmian)**
- Grok dołożył 5 commitów: stopkę, FAQ, strony prawne, sekcje bloga i wpis w seedzie, nowe teksty strony głównej.
- Zmiany ważne dla frameworka:
  - **Schemat:** `BlogPost.blocksJson` (`String`, domyślnie `"[]"`). Kolumna jest dodawana z wartością domyślną, więc `db push` przeszedł na istniejącym wolumenie bez `down -v`.
  - **Seed:** wpis `kombinezon-zamiast-sukienki` tworzony tylko wtedy, gdy go brakuje. Ma stały układ strony (`blog-kombinezon.tsx`), nie używa `blocksJson`.
  - **API admina bloga:** zapis przyjmuje pole `blocks` (tekst, zdjęcie z tekstem, karty), co trzeba uwzględnić w schematach `/api/admin/*`. Kontrakt `/api/commerce/*` się nie zmienił.
  - **`output: "standalone"` tylko przy `DOCKER_BUILD=1`** (ustawiane w Dockerfile), więc Vercel buduje się jak dawniej.
- Docker: `up -d --build --wait` daje kod 0 po 260 s (`package-lock` bez zmian, przyczyny dłuższego czasu nie badałem). Obrazy: `runner` 411 MB, `builder` 1,33 GB. `/blog` i `/szycie-na-miare` są oznaczone `ƒ`, `/blog/[slug]` `●`; nowe strony (`/faq`, `/regulamin` i inne) są statyczne (`○`). Kody 200: wszystkie strony, wpis bloga, zdjęcia z `public/preview/blog` i `chapters`, wyszukiwarka. Nieistniejący wpis zwraca 404.
- STG: nowa wersja jest wdrożona (nowy hero, `/faq` 200, wpis bloga z seedu widoczny, a więc seed przeszedł na Neonie). Wpis na STG jest prerenderowany w buildzie (`x-nextjs-prerender: 1`), a w Dockerze renderuje się przy pierwszym wejściu, bo w czasie builda nie ma bazy.
- **Dane STG odbiegają od seedu:** `search?q=castello` różni się jednym polem (`isNew` na STG `true`, w seedzie `false`). Seed tylko dopisuje brakujące rekordy (`if (existing) continue`), więc zmiany zrobione w adminie na STG zostają. Testy na STG nie mogą więc zakładać wartości z seedu; sprawdzają kształt odpowiedzi (kontrakt) albo własne dane `test-`.
- Na dysku C: zostało 11 GB (wcześniej 29 GB): kolejne buildy zostawiają stare warstwy i cache.

**Projekt:** [`docs/superpowers/specs/2026-11-01-etap-1-docker-design.md`](docs/superpowers/specs/2026-11-01-etap-1-docker-design.md) · **Notka dla Groka:** [`docs/handoff/2026-11-01-etap-1-docker.md`](docs/handoff/2026-11-01-etap-1-docker.md)

> Implikacje z Etapu 0 (entrypoint z `prepare-database`) zastąpione przez usługę `db-init` — patrz projekt.

### Etap 2 — 2026-11-06 → 2026-11-06

**Repo publiczne:** <https://github.com/ironz1/jersa_test_framework> (CI `ci` zielone na `main`).

**Co powstało**
- Projekt uv (Python 3.12, `pyproject.toml`, `uv.lock`), pakiet `src/jersa/`: `config.py` (Settings), `clients/api_client.py`, `db/connection.py`, `schemas/loader.py`, `pages/product_page.py`, fixtures w `src/jersa/fixtures/`.
- Fixtures: `settings`, `base_url`, `api_client` (nowa sesja na test), `db` (pomijana bez `DATABASE_URL`), `assert_matches_schema`, `page` z pytest-playwright.
- Schematy `schemas/product.json` (22 pola) i `schemas/search.json`, spisane z odpowiedzi i `src/commerce/types.ts` sklepu.
- Testy smoke: kontrakt wyszukiwarki, pusty koszyk, CASTELLO w bazie, nagłówek strony produktu. Testy frameworka: 18 (Settings, loader schematów, ApiClient, połączenie z bazą).
- `.github/workflows/ci.yml`: ruff i testy frameworka. `README.md`.

**Wyniki**
- `uv run pytest -m smoke` → 4 passed (Docker); cały zestaw → 26 passed w ok. 1 s (22 + 4 testy dodane po przeglądzie).
- Kontrakt przechodzi na DEV i na STG; schemat sprawdzony na wszystkich produktach (5 na DEV, 8 na STG).
- Celowo zepsuty schemat daje `$.products[0]: Additional properties are not allowed ('hidden' was unexpected)`.
- Bez `DATABASE_URL` test bazy jest pomijany z komunikatem. CI zasymulowane lokalnie bez `.env`: zielone.
- Przegląd całej gałęzi przez niezależnego recenzenta: 3 ważne uwagi naprawione (hasła w błędzie walidacji, ignorowane `--base-url`, dane osobowe w historii), 7 drobnych odłożonych.
- Przed pierwszym pushem historia przepisana `git filter-repo --replace-text`: ścieżki `C:\Users\<login>\...` zamienione na względne, usunięte fragmenty prywatnych adresów. Po pushu nie dałoby się tego cofnąć.

**Projekt:** [`docs/superpowers/specs/2026-11-06-etap-2-szkielet-design.md`](docs/superpowers/specs/2026-11-06-etap-2-szkielet-design.md) · **Plan:** [`docs/superpowers/plans/2026-11-06-etap-2-szkielet.md`](docs/superpowers/plans/2026-11-06-etap-2-szkielet.md)

### Etap 3, krok A — 2026-11-12 → 2026-11-13

**Co powstało**
- **Reguły i scenariusze przed kodem.** 24 reguły biznesowe sklepu spisane z kodu i referencji API, potwierdzone przez właściciela sklepu. Z nich 73 przypadki testowe z ID.
- **Macierz śledzenia wymagań:** `docs/traceability.json` → [`docs/traceability-matrix.pdf`](docs/traceability-matrix.pdf). Opis mechanizmu: sekcja 7.
- **Klient `CommerceApi`** (`src/jersa/clients/commerce.py`): jedna metoda na endpoint, fixtures `shop` i `make_shop` (dwóch niezależnych klientów w jednym teście).
- **Własny produkt na test** (ADR-012): `src/jersa/db/products.py`, fixtures `make_product`, `product`, `placed_order`. Produkt `test-<hex>` wstawiany SQL-em, usuwany po teście razem z zamówieniami i opiniami.
- **7 nowych schematów kontraktu:** koszyk, przechowalnia, opinie, utworzone zamówienie, start płatności, powiadomienie o płatności, błąd 400.
- **Testy sklepu:** kontrakt 10, API 51, baza 17, E2E 5. Page objecty: produkt, kasa, zamówienie, wyszukiwarka, przechowalnia.
- `PAYU_MODE: mock` w `docker-compose.yml`: tryb płatności testowej.

**Wyniki**
- `uv run pytest` → 148 passed w ok. 12 s (83 testy sklepu + 65 testów frameworka). `-m smoke` → 9 passed.
- Trzy przebiegi z rzędu bez `down -v`: za każdym razem tyle samo zielonych, stan magazynowy seeda bez zmian (ta sama suma kontrolna), w bazie zero produktów, zamówień, opinii, koszyków i przechowalni testów (po przeglądzie: przyrost wierszy koszyków i przechowalni na przebieg spadł z 41 i 5 do 0).
- Odwrócona kolejność katalogów: zielone. Bez `DATABASE_URL`: testy z własnym produktem pomijane z komunikatem.
- Kontrola czerwieni w każdej grupie: celowo zmieniona oczekiwana wartość daje czytelną porażkę, np. `$.lines[0]: Additional properties are not allowed ('quantity' was unexpected)` albo `Locator expected to have text '201,00 zł' / Actual value: 200,00 zł`.
- Usunięcie kolumny z `product_row()` daje `product_row() nie wypełnia wymaganych kolumn ProductRow: ['description']`.

**Czego się nauczyłem**
- Spisanie reguł przed testami ujawnia rzeczy, których nikt nie zapisał: 8 z 24 reguł wyszło dopiero przy łączeniu przypadków z wymaganiami.
- Seed nie nadaje się na dane testów, które coś zmieniają: kilkanaście testów zamawia towar, a seed ma po 5 sztuk i żadnego produktu z procentem promocji.
- Test E2E może potwierdzić płatność przez API zamiast klikania: liczy się krok klienta, nie droga do niego.

**Projekt:** [`docs/superpowers/specs/2026-11-13-etap-3-warstwy-testow-design.md`](docs/superpowers/specs/2026-11-13-etap-3-warstwy-testow-design.md) · **Plan:** [`docs/superpowers/plans/2026-11-13-etap-3-krok-a-warstwy-testow.md`](docs/superpowers/plans/2026-11-13-etap-3-krok-a-warstwy-testow.md) · **ADR:** 012, 013, 014

### Etap 4 — 2026-11-16 → 2026-11-16

**Co powstało**
- `pytest-xdist` w grupie `dev`, `-n 4` w `addopts` (`pyproject.toml`). Test `tests/framework/test_pytest_config.py` pilnuje, że xdist jest zainstalowany, a `-n 4` zostaje w konfiguracji.
- W `ci.yml` testy frameworka idą z `-n 0`.
- Dokumentacja: `-n 0` do debugowania i podglądu (`docs/komendy.md`, `README.md`, `.env.example`, `CLAUDE.md`).

**Wyniki**
- Pierwszy przebieg na 4 procesach: 150 passed, **zero kolizji**, bez żadnej poprawki testów. Dzięki własnemu produktowi na test i sesjom koszyka na test (Etap 3) testy już były niezależne.
- Trzy przebiegi z rzędu na świeżej bazie: za każdym razem 150 passed, w bazie 0 koszyków, przechowalni, zamówień i produktów `test-*`, ta sama suma kontrolna seeda (`db119c26…`). Szczyt połączeń do Postgresa: 10 z limitu 100.
- **Czas: bez istotnego zysku.** Dwie sesje pomiarowe: tuż po włączeniu 11,2 s (jeden proces) wobec 10,3 s (cztery), po odbudowie bazy ok. 15 s w obu przypadkach. API, baza i kontrakt: 5,3 → 4,4 s. E2E: 6,3 → 8,0 s, bo każdy z 4 procesów uruchamia własną przeglądarkę. Zestaw frameworka: 0,5 s → 4,8 s (koszt startu procesów), dlatego w CI zostaje `-n 0`.

**Czego się nauczyłem**
- Równoległość jest przede wszystkim testem niezależności, a nie sposobem na szybkość. Przy 150 krótkich testach stały koszt startu procesów (a w E2E własnej przeglądarki w każdym) zjada zysk. Czy ogranicza też sklep, nie mierzyłem.
- Mierzę, zanim uznam, że coś przyspiesza. Dopiero większy zestaw pokaże, czy równoległość się opłaca; wtedy warto zmierzyć też obciążenie sklepu (CPU kontenera, czasy odpowiedzi).

**Projekt:** [`docs/superpowers/specs/2026-11-16-etap-4-rownoleglosc-design.md`](docs/superpowers/specs/2026-11-16-etap-4-rownoleglosc-design.md) · **Plan:** [`docs/superpowers/plans/2026-11-16-etap-4-rownoleglosc.md`](docs/superpowers/plans/2026-11-16-etap-4-rownoleglosc.md) · **ADR:** 015

### Etap 5A — 2026-11-17 → 2026-11-17

**Co powstało**
- Workflow `tests` w repo **sklepu** (`.github/workflows/tests.yml`): na każdym PR do `main` buduje sklep z kodu PR-a w Dockerze, pobiera publiczne repo testów (gałąź o tej samej nazwie albo `main`), uruchamia cały zestaw (150 testów, 4 procesy) i zgłasza status `tests`. Artefakty: ślady Playwrighta i logi kontenerów przy porażce.
- Zasady pracy przez pull requesty dla agenta sklepu w jego `AGENTS.md`.

**Wyniki**
- Przebieg na PR-ze trwa ok. 4 minuty: start sklepu 191 s (budowa obrazu, seed i healthcheck razem; osobno nie mierzone), instalacja przeglądarki 23 s, same testy 10 s. Dominuje start sklepu, więc to on jest pierwszym kandydatem do optymalizacji (cache, gotowy obraz); najpierw warto zmierzyć, ile z tego to sama budowa.
- **Kontrola czerwieni:** tymczasowy PR z celowo zmienionym zaokrąglaniem ceny (`Math.round` → `Math.floor`) dał czerwony status: 1 test nie przeszedł (`test_promo_price_rounds_half_up`, `assert 22 == 23`), 149 przeszło. PR zamknięty bez scalania.
- Symulacja CI lokalnie na czystym klonie repo testów, bez `.env`: pierwszy przebieg miał 1 porażkę (E2E `test_guest_buys_product`, szuflada koszyka niewidoczna w 5 s), 149 passed, a cały przebieg trwał 60 s zamiast ok. 15 s, bo maszyna była obciążona tuż po budowie obrazu. Porażki nie udało się odtworzyć: test sam trwał potem 0,8 s, trzy kolejne pełne przebiegi dały 150 passed w ok. 7 s, a hipotezę o klikaniu przed hydracją Reacta odrzucił pomiar (przy 40-krotnie spowolnionym procesorze stary kod też przechodzi z dłuższym limitem). Poprawki w page objectach nie wprowadziłem, żeby nie zgadywać; workflow zachowuje ślady Playwrighta na wypadek, gdyby to wróciło.
- **Ograniczenie planu:** reguła ochrony `main` jest zapisana, ale GitHub jej **nie egzekwuje** w prywatnym repo na darmowym planie (API: „Upgrade to GitHub Pro or make this repository public”). Bramka jest więc informacyjna: czerwony status widać przy PR-ze, ale Merge nie jest blokowany. (Wniosek z API: `protected: false`. Próbnego pushu na `main` nie robiłem, bo deployuje na Vercel.) Decyzja właściciela: zostajemy przy tym, a egzekwowanie dodajemy przez płatny plan albo bramkę na wdrożeniu (5B).

**Czego się nauczyłem**
- Zielony przebieg niczego nie dowodzi. Dopiero celowo zepsuta zmiana pokazała, że bramka umie być czerwona i że komunikat wskazuje regułę.
- Bramka musi być odporna na chwilowe awarie niezwiązane ze zmianą (sieć przy `npm ci`), inaczej uczy ludzi ignorować czerwony status.
- Przed zbudowaniem bramki sprawdzić, czy plan GitHuba pozwala ją egzekwować. Ustawienie reguły bez egzekwowania wygląda jak ochrona, a nią nie jest.

**Projekt:** [`docs/superpowers/specs/2026-11-17-etap-5a-bramka-sklepu-design.md`](docs/superpowers/specs/2026-11-17-etap-5a-bramka-sklepu-design.md) · **Plan:** [`docs/superpowers/plans/2026-11-17-etap-5a-bramka-sklepu.md`](docs/superpowers/plans/2026-11-17-etap-5a-bramka-sklepu.md) · **ADR:** 016

<!--
### Etap N — <data rozpoczęcia> → <data zakończenia>
- **Zrobione:**
- **Nauczyłem się:**
- **Powiązane:** ADR-001, ...
-->

### Ryzyka (z założeń, do weryfikacji w trakcie)

| Temat | Uwaga |
|---|---|
| Prisma: SQLite vs Postgres | ✅ Wyjaśnione (Etap 0): `COMMERCE=own` + URL Postgres + `prepare-database.mjs` w usłudze `db-init` |
| Konteneryzacja Next.js | Największe ryzyko techniczne etapów 0–1; konkretnie: prerender stron z bazy w `next build` (rozwiązanie: ADR-007) |
| Koszty AWS | RDS i App Runner płatne — budżet, alerty, wyłączanie stagingu |
| Deploy App Runnera | Asynchroniczny — smoke musi czekać na status RUNNING |
| RDS | Prywatny; weryfikacja bazy na Postgresie z Dockera, na stagingu przez API |
| Wywołania między repo | `repository_dispatch` i checkout prywatnego repo wymagają PAT lub GitHub App; `GITHUB_TOKEN` działa tylko w obrębie jednego repo |
| Cron w GitHub Actions | Chodzi w UTC — `0 2 * * *` to 3:00/4:00 czasu polskiego; godzinę trzeba przeliczyć |
| Czas budowy obrazu sklepu w CI | Kilka minut na przebieg; później cache warstw lub gotowy obraz z GHCR |
| Vercel preview | Deployment Protection — sprawdzić bypass dla testów |
| Brak endpointów kasujących | Sprzątanie zamówień, płatności i opinii przez SQL |
| Stan magazynowy (5 szt./rozmiar) | ✅ Wyjaśnione (ADR-012, Etap 4): własny produkt na test; 3 przebiegi na 4 procesach bez kolizji |
| Brak migracji (`db push`) | Zmiana schematu w sklepie może cicho zepsuć zapytania SQL w testach DB |

---

## 3. Architektura

### Środowisko testowe (gdzie co działa)

Rozrysowane: [`docs/mapa-srodowiska.pdf`](docs/mapa-srodowiska.pdf).

```
┌──────────── Mój komputer / runner CI ────────────┐
│                                                  │
│  pytest (IDE, venv)  ──HTTP──► :3100 ─┐  Docker  │
│   - API (requests)                    ▼          │
│   - E2E (Playwright)          app: sklep Next.js │
│   - DB (psycopg)  ──SQL──► :5432 ─┐   │ SQL      │
│                                   ▼   ▼          │
│                              postgres:16         │
└──────────────────────────────────────────────────┘
```

- **W Dockerze jest tylko SUT:** sklep + Postgres. Framework działa **poza** Dockerem, na hoście (IDE, terminal, runner CI) — łatwe debugowanie, breakpointy, widoczna przeglądarka.
- **Uruchomiony Docker = prywatna instancja sklepu** — jak mały staging na laptopie. Świeżą bazę daje `down -v`; zwykły restart zachowuje dane.
- **Wystawianie portów** (`ports: ["127.0.0.1:3100:3000"]` w `docker-compose.yml`, format `host:kontener`): sklep widoczny jako `127.0.0.1:3100`, baza jako `127.0.0.1:5432` (w `.env` adres `127.0.0.1`, nie `localhost`: patrz sekcja 6). Bez `ports` nic spoza Dockera nie widzi kontenera.
- **Wewnątrz Dockera** kontenery rozmawiają po nazwie serwisu (`postgres:5432`), nie przez `localhost`.
- **Te same testy, różne cele:** testy czytają cel z `.env`: `BASE_URL`, a testy i fixtures używające SQL także `DATABASE_URL`. Bez zmiany obu HTTP poszłoby na STG, a SQL na lokalną bazę.

| | Docker lokalnie | Staging (Vercel) |
|---|---|---|
| Kto stawia | ja, `docker compose up` | Vercel, po deployu |
| Dane na starcie | zawsze te same (seed) | to, co zostało po poprzednich testach i ludziach |
| Silnik bazy | Postgres | Postgres (Neon) |
| Testy DB (psycopg 3) | tak, bezpośrednio | zależy od otwartej decyzji o sekrecie Neona w CI; bez niego stan tylko przez API |
| Co sprawdza | czy kod sklepu działa | czy działa wdrożona wersja |
| Kiedy | codziennie + CI na push | nightly regression + smoke po deployu |

**Jeden przebieg:** `docker compose up` (Postgres → `db-init`: schemat + seed → sklep) → healthcheck (`/api/commerce/search?q=castello` zwraca CASTELLO) → `pytest` → `docker compose down -v` (wszystko znika).

**Docker ≠ CI.** Docker odpowiada na pytanie *jak* postawić środowisko; CI (GitHub Actions) — *kiedy* i *co* uruchomić. CI używa Dockera jako narzędzia i powtarza te same komendy co lokalnie, dlatego Etap 1 (Docker) jest przed Etapem 5 (CI).

### CI — jak to działa (GitHub Actions)

- **Runner:** po zdarzeniu (push, PR, cron) GitHub uruchamia świeżą maszynę wirtualną (Ubuntu z Dockerem, Pythonem, gitem), wykonuje kroki z `.github/workflows/*.yml` i niszczy ją po zakończeniu. Każdy przebieg od zera.
- **Docker i pytest działają na tym samym runnerze** → `127.0.0.1:3100` działa jak na laptopie. Mapa środowiska pasuje do CI 1:1 — „mój komputer” zamienia się na runner.

```
zdarzenie (PR sklepu / push testów)
  → runner: czyste Ubuntu
    1. checkout repo testów
    2. checkout repo sklepu (gałąź PR-a lub main; prywatne → token)
    3. docker compose up --build --wait   (sklep + Postgres + seed, czeka na healthchecki)
    4. setup Pythona, pip install, playwright install --with-deps chromium
    5. pytest                             (127.0.0.1:3100, :5432)
    6. upload raportu, trace, wideo       (if: always() — także po porażce)
    7. docker compose down -v
  → status ✅/❌ przy PR/commicie + artefakty + logi
```

- **Wynik:** status przy PR (z egzekwowaną branch protection czerwony blokuje merge; w prywatnym repo na darmowym planie jest tylko informacją, ADR-016), artefakty w zakładce Actions (raport HTML, trace Playwrighta → `playwright show-trace`, wideo), logi kroków (warto dodać `docker compose logs` przy porażce).
- **Wyzwalacze:** ADR-005.
- **Dlaczego Docker także przy zmianie w repo testów:** testy to też kod. Na znanej wersji sklepu z czystym seedem zmienia się tylko jedna rzecz — porażka wskazuje na zmianę w testach. Na stagingu porażka byłaby niejednoznaczna (zmienione dane? nowy deploy? staging leży?), a testy DB w ogóle by nie działały.

### CI — konfiguracja w GitHubie (plan na Etap 5)

1. Repo testów na GitHubie (`ironz1/jersa_test_framework`, **publiczne**).
2. ~~Token do odczytu repo testów~~ **niepotrzebny w 5A**: repo testów jest publiczne, więc `actions/checkout` pobiera je bez tokena (ADR-016). Token (PAT do prywatnego sklepu, jako sekret repo testów) będzie potrzebny dopiero w 5B, gdy job w repo testów zacznie budować sklep.
3. Workflow w repo **sklepu** `.github/workflows/tests.yml` — **to on jest zapalnikiem** (`on: pull_request: branches: [main]`); docker-compose to tylko krok w środku: checkout sklepu (PR) → wybór gałęzi testów (ta sama nazwa albo `main`) → checkout testów (bez tokena, repo publiczne) → `uv sync` + `playwright install` → `docker compose up --build --wait` (`STOREFRONT_PATH` = sklep z PR-a, do 3 prób) → pytest → upload śladów (`if: always()`) i logów kontenerów (przy porażce) → `down -v`.
4. Branch protection na `main` sklepu: wymagany zielony status `tests` → CI staje się bramką. **Uwaga:** w prywatnym repo na darmowym planie reguła jest zapisana, ale nieegzekwowana (patrz ADR-016).
5. Praca w sklepie przez PR-y (push na `main` omija bramkę). Zasady dla agenta: `AGENTS.md` w repo sklepu.
6. W repo testów osobny workflow: `push`/`pull_request` (Docker, `main` sklepu) + `schedule` (nightly na STG).

### Mapowanie środowisk (klasyczne DEV/INT/STG/PROD → jersa)

| Klasycznie | jersa | Rola |
|---|---|---|
| DEV | Docker lokalnie | praca developera, pisanie testów |
| INT | Docker w CI (GitHub Actions) | bramka na PR sklepu + testy na push w repo testów |
| STG | `jersa-storefront.vercel.app` — piaskownica bez ruchu (Neon); później AWS | nightly regression, smoke po deployu; zapisy dozwolone, ale baza trwała → dane testu własne i sprzątane po ID |
| PROD | osobne środowisko właściwego sklepu (jeszcze nie istnieje) | klienci; później tylko smoke tylko do odczytu (shift-right) |

- Tymczasowe środowisko (Docker w CI) przejmuje rolę INT **tylko dlatego, że system jest mały**: jedna aplikacja, jedyna zależność zewnętrzna (PayU) na mocku.
- INT jako wspólne środowisko wraca do gry, gdy jest wiele serwisów różnych zespołów, prawdziwe integracje zewnętrzne (sandbox płatności, SSO, kolejki), proces wdrożenia z migracjami na trwałej bazie, infrastruktura bliska produkcji. W jersa: dopiero przy Etapie 8 (wydzielony backend) — wtedy także testy kontraktowe (Pact).

### Warstwy

```
<!-- diagram warstw, np.:
tests/          → scenariusze testowe (co testujemy)
pages/ | api/   → abstrakcje nad aplikacją (jak z nią rozmawiamy)
core/           → konfiguracja, logowanie, klienci, utils
-->
```

### Struktura katalogów

<!-- katalog → po co istnieje -->

### Przepływ wykonania testu

<!-- od komendy CLI → konfiguracja → fixtures → test → teardown → raport -->

---

## 4. Dziennik decyzji (ADR — Architecture Decision Records)

### Otwarte decyzje

| Temat | Kiedy rozstrzygnąć | Dlaczego wtedy |
|---|---|---|
| Strategia stanu magazynowego w testach zamówień | Etap 3, przed pierwszym testem zamówienia | **Rozstrzygnięte 2026-11-13: ADR-012** (własny produkt na test, potwierdzone na działającym sklepie). Kandydat z 2026-11-01: test wstawia własny `ProductRow` (`test-<uuid>`, własne `stockBySize`), zamawia go, teardown usuwa zamówienie i produkt — seed nietknięty (ADR-003). Do potwierdzenia na działającym sklepie |
| Dostęp testów do bazy STG (Neon) z CI | Etap 3/5 | Fixtures tworzące dane przez SQL na STG wymagają sekretu `DATABASE_URL` Neona w GitHub Actions; ADR-005 zakładał nightly bez testów DB |
| Kolejne wpisy bloga w seedzie | Gdy będą gotowe treści | **Częściowo rozstrzygnięte (2026-11-05):** Grok dodał wpis `kombinezon-zamiast-sukienki` (zdjęcie z `public/`, tylko dopisywanie). Wpis usunięty w adminie wróci po następnym deployu. Do ustalenia, czy kolejne wpisy też trafiają do seedu |
| Przeniesienie treści bloga na PROD | Przed uruchomieniem właściwego sklepu | Wpisy z admina na STG nie przejdą same: plik w repo albo migracja z bazy |
| Praca w sklepie przez PR-y zamiast pushy na `main` | Przed Etapem 5 | **Rozstrzygnięte 2026-11-17:** przez PR-y, zasady w `AGENTS.md` sklepu; techniczne wymuszenie wymaga płatnego planu (patrz wiersz niżej). Bramka na PR (ADR-005) działa tylko, gdy zmiany idą przez PR; push na `main` deployuje od razu |
| Egzekwowanie bramki na `main` sklepu | 5B | Na darmowym planie reguła ochrony w prywatnym repo nie działa (ADR-016). Opcje: GitHub Pro albo bramka na wdrożeniu (auto-deploy z `main` wyłączony, workflow wdraża dopiero po zielonych testach) |
| Mechanizm bramki na PR sklepu: workflow sklepu sam pobiera repo testów (checkout z tokenem) czy `repository_dispatch` / reusable workflow | Etap 5 | **Rozstrzygnięte 2026-11-17: ADR-016** (checkout w workflow sklepu, bez tokena, bo repo testów jest publiczne). Status musi wrócić do PR-a sklepu; `repository_dispatch` nie raportuje wyniku do PR-a automatycznie |
| Budowanie obrazu sklepu przy każdym przebiegu czy gotowy obraz z GHCR | Etap 5 (optymalizacja) lub Etap 6 | Gotowy obraz skraca start z minut do sekund; ten sam mechanizm posłuży do ECR w AWS |
| Narzędzie raportów: pytest-html czy Allure | Etap 5 | Raporty trafiają do CI dopiero w Etapie 5; historia przebiegów w Allure ma sens przy regularnych uruchomieniach. Porównanie: sekcja 9 |
| mypy i pre-commit | Po Etapie 3 | Przy kilku plikach szkieletu koszt konfiguracji przewyższa zysk; po Etapie 3 będzie dość kodu, żeby ocenić |
| Czy framework też uruchamiać w kontenerze | Najpóźniej Etap 6 (AWS) | Na start framework na hoście (debugowanie); obraz frameworka (np. `mcr.microsoft.com/playwright/python`) ma sens, gdy testy mają działać poza laptopem i CI |

### ADR-001: Framework w osobnym repozytorium, w Pythonie
- **Data:** 2026-10-26
- **Kontekst:** sklep jest w TypeScripcie i ma już testy Playwright w TS; portfolio celuje w role Python SDET.
- **Rozważane opcje:**
  - A — testy w repo sklepu (TS) — blisko kodu, ale nie pokazuje Pythona
  - B — osobne repo w Pythonie — niezależny cykl życia, testuje aplikację jak „klient z zewnątrz”
- **Decyzja:** B.
- **Konsekwencje:** framework testuje sklep przez HTTP, przeglądarkę i bazę — jak w firmie z osobnym zespołem QA. Koszt: synchronizacja wersji między repo (smoke po deployu, repository_dispatch).
- **Na rozmowie:** <!-- do uzupełnienia własnymi słowami -->

### ADR-002: Kontrakt API przez jsonschema, bez Pact
- **Data:** 2026-10-26
- **Kontekst:** API nie ma OpenAPI; frontend i backend są w jednej aplikacji Next.js.
- **Rozważane opcje:**
  - A — Pact (consumer-driven contracts) — wymaga dwóch niezależnych stron kontraktu
  - B — jsonschema spisywane ręcznie z realnych odpowiedzi, `additionalProperties: false`
- **Decyzja:** B. Pact wraca jako opcja po wydzieleniu backendu (Etap 8).
- **Konsekwencje:** szybki start i pełna kontrola; koszt: ręczne utrzymanie schematów.
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-003: Izolacja danych testowych przez prefiks uuid i teardown po ID
- **Data:** 2026-10-26
- **Kontekst:** staging jest współdzielony; testy mają działać równolegle (pytest-xdist) i wielokrotnie.
- **Rozważane opcje:**
  - A — czyszczenie całych tabel przed/po testach — proste, ale niszczy cudze dane i blokuje równoległość
  - B — unikalny prefiks w danych każdego testu, teardown usuwa tylko własne rekordy po ID
- **Decyzja:** B (opcjonalnie branch Neon na przebieg).
- **Konsekwencje:** testy niezależne i powtarzalne; koszt: każda fixture tworząca dane musi umieć po sobie posprzątać (dla zamówień przez SQL — brak endpointów kasujących).
- **Doprecyzowanie (2026-11-01):** izolacja na poziomie **testu**, nie zestawu. Reset bazy przed zestawem odrzucony: na trwałym STG koliduje z równoległymi przebiegami (nightly + smoke) i workerami xdist, a na PROD byłby niemożliwy. W Dockerze świeża baza per przebieg przychodzi za darmo (`down -v`).
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-004: CI w GitHub Actions, AWS dopiero po działającym CI
- **Data:** 2026-10-26
- **Kontekst:** sklep jest na GitHubie; AWS jest celem nauki, ale kosztuje.
- **Decyzja:** GitHub Actions jako jedyne CI (bez Azure DevOps i GitLab CI); AWS (ECR, App Runner, RDS) dopiero w Etapie 6.
- **Konsekwencje:** etapy 0–5 dają kompletne portfolio za darmo; AWS nie blokuje postępu.
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-005: Wyzwalacze CI — główna bramka na PR sklepu
- **Data:** 2026-10-27
- **Kontekst:** pierwotny plan (PDF z 26.10) testował sklep w CI tylko przy pushu w repo testów, nightly i po deployu — czyli zmiany w **sklepie** były sprawdzane dopiero **po** wdrożeniu na staging. Najważniejsze pytanie brzmi: czy nowy kod sklepu niczego nie psuje — i odpowiedź ma przyjść przed merge.
- **Rozważane opcje:**
  - A — tylko push w repo testów + nightly + smoke po deployu (plan z PDF) — błąd sklepu wykrywany dopiero na stagingu
  - B — dodatkowo bramka na PR w repo sklepu: testy na Dockerze z kodem z gałęzi PR-a, wynik przy PR-ze
- **Decyzja:** B. Cztery wyzwalacze:

  | Trigger | Wersja sklepu | Cel testów | Po co |
  |---|---|---|---|
  | PR w repo **sklepu** | gałąź PR-a | Docker na runnerze | **główny:** łapie błędy sklepu przed merge |
  | Push / PR w repo **testów** | `main` sklepu | Docker na runnerze | czy zmienione testy działają (zmienia się tylko jedna rzecz) |
  | Nightly (cron) | staging | Vercel | pełny regression na wdrożonej wersji (testy DB zależą od otwartej decyzji o dostępie do Neona) |
  | Po deployu | staging | Vercel | szybki smoke: czy wdrożenie się udało |

- **Konsekwencje:** w repo sklepu pojawia się workflow (architektura sklepu bez zmian); potrzebny token do odczytu prywatnego repo; czerwony wynik może blokować merge (branch protection). Koszt: dłuższy PR w sklepie o czas budowy obrazu.
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-006: Dockerfile w repo sklepu, compose w repo testów
- **Data:** 2026-11-01
- **Kontekst:** testy potrzebują obrazu sklepu; sklep zmienia się szybko i pisze go inny agent (Grok).
- **Rozważane opcje:**
  - A — Dockerfile i compose w repo testów — pełna kontrola bez zmian w sklepie, ale Dockerfile po cichu się psuje przy zmianach sklepu (Node, zależności, build), a bramka na PR wymaga synchronizacji dwóch repo
  - B — Dockerfile w repo sklepu, compose w repo testów — obraz zmienia się w tym samym commicie co kod; PR sklepu buduje obraz z własnego Dockerfile
- **Decyzja:** B. Przygotowanie bazy w osobnej usłudze `db-init` (etap `builder`), aplikacja jako czysty obraz standalone.
- **Konsekwencje:** zmiany w sklepie wprowadza Grok według notki (`docs/handoff/`), zasady trafiają do `CLAUDE.md` sklepu; repo testów niczego w sklepie nie commituje. Później obraz publikuje CI sklepu (GHCR/ECR).
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-007: Obraz sklepu budowany bez bazy, strony z danymi renderowane w czasie działania
- **Data:** 2026-11-05
- **Kontekst:** `docker build` nie ma dostępu do Postgresa, bo compose startuje bazę dopiero po zbudowaniu obrazu. Na Vercelu baza jest dostępna w buildzie, więc problem był tam niewidoczny. `/blog` wywracał build, a `/szycie-na-miare` zapisywała w obrazie dane z mocka bez odświeżania.
- **Rozważane opcje:**
  - A — `try/catch` w `/blog` — mała zmiana, ale chwilowa awaria bazy nadpisałaby cache ISR pustą listą; pierwsze wejście w kontenerze też mogłoby dać pustą stronę
  - A′ — `try/catch` tylko w fazie builda (`NEXT_PHASE`) — Vercel bez zmian, ale wewnętrzna zmienna Next i ryzyko niestabilnych testów
  - B — `force-dynamic` na stronach czytających bazę — obraz niezależny od bazy, testy widzą stan Postgresa; koszt: odczyt z bazy przy każdym wejściu, także na Vercelu
  - C — baza dostępna w `docker build` — bez zmian w aplikacji, ale build w dwóch fazach zamiast `compose up --build`
  - D — `--experimental-build-mode compile` — tryb eksperymentalny
- **Decyzja:** B, tylko `/blog` i `/szycie-na-miare`. `/blog/[slug]` bez zmian, bo nie blokuje builda i czyta bazę przy pierwszym wejściu.
- **Konsekwencje:** ten sam obraz działa w każdym środowisku, a build jest oddzielony od danych. Blog traci ISR, więc przed uruchomieniem właściwego sklepu trzeba sprawdzić czas odpowiedzi tych stron. Poprzedni commit powstał bez builda, bo Docker wtedy nie działał; naprawę sprawdzono uruchomieniem.
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-008: Python 3.12, uv i jeden `pyproject.toml`
- **Data:** 2026-11-06
- **Kontekst:** szkielet potrzebuje powtarzalnej instalacji lokalnie (Windows) i w CI (Ubuntu). Systemowy Python to 3.11.
- **Rozważane opcje:**
  - A — `requirements.txt` + pip + venv — najbardziej znane, ale zwykle bez blokady zależności przechodnich, a konfiguracja pytest i ruff w osobnych plikach
  - B — Poetry — dojrzałe, ale wolniejsze i z własnym formatem sekcji
  - C — uv + `pyproject.toml` + `uv.lock` — jeden plik konfiguracji (PEP 621), blokada wszystkich wersji, szybka instalacja, uv sam instaluje Pythona 3.12
- **Decyzja:** C. Python 3.12 (`.python-version`), konfiguracja pytest i ruff w `pyproject.toml`, bez `pytest.ini` i `requirements.txt`. `[tool.uv] package = false`, bo framework nie jest instalowanym pakietem.
- **Konsekwencje:** `uv sync --locked` daje lokalnie i w CI te same wersje. Ruff 0.17 formatuje też bloki Pythona w plikach Markdown. `requirements.txt`, gdyby był potrzebny: `uv export`.
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-009: Konfiguracja przez pydantic-settings, kod w `src/jersa`, fixtures w modułach
- **Data:** 2026-11-06
- **Kontekst:** poprzedni framework miał stan globalny i jeden `conftest.py` na 2500 linii. Testy mają działać lokalnie, w CI i na STG, równolegle (Etap 4).
- **Rozważane opcje:**
  - Konfiguracja: `python-dotenv` + `os.getenv` (prościej, bez walidacji) albo **pydantic-settings** (typy, walidacja przy starcie, zmienne środowiskowe wygrywają z `.env`)
  - Układ: płaskie `src/{clients,db,...}` (nazwy mogą kolidować z bibliotekami) albo **pakiet `src/jersa/`** dołączany przez `pythonpath = ["src"]`
  - Fixtures: wszystko w `conftest.py` albo **moduły `src/jersa/fixtures/*.py`** ładowane przez `pytest_plugins`
- **Decyzja:** pydantic-settings, pakiet `src/jersa/`, fixtures w modułach. `Settings` szuka `.env` po ścieżce absolutnej od katalogu projektu, a fixture `base_url` w głównym `conftest.py` nadpisuje tę z pytest-base-url (z niej korzysta pytest-playwright).
- **Konsekwencje:** brak albo zły `BASE_URL` daje czytelny błąd przed pierwszym testem; testy działają niezależnie od katalogu uruchomienia. Fixture `_verify_url` z pytest-base-url jest autouse i wymusza `base_url`, więc testy frameworka (`tests/framework/`) mają własną fixture `base_url` z adresem zastępczym i nie potrzebują `.env`. Opcja `--base-url` z linii poleceń wygrywa z `BASE_URL` z `.env` (wcześniej była po cichu ignorowana i testy szły na DEV). Błąd konfiguracji ma postać jednej linii ze zmienną i `.env.example`, a `hide_input_in_errors=True` nie pozwala pydanticowi wypisać haseł z innych zmiennych.
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-010: psycopg 3 zamiast psycopg2
- **Data:** 2026-11-06
- **Kontekst:** testy DB i fixtures danych potrzebują sterownika Postgresa działającego na Windows i w CI.
- **Rozważane opcje:**
  - A — psycopg2 — najbardziej rozpowszechniony, ale w trybie utrzymania; wersja ze źródeł wymaga kompilatora
  - B — psycopg 3 (`psycopg[binary]`) — aktywnie rozwijany następca, prostsze API (`conn.execute`, `dict_row`), gotowe binaria
- **Decyzja:** B. Połączenie w trybie autocommit, wiersze jako słowniki, `connect_timeout=5`.
- **Konsekwencje:** niedziałająca baza daje błąd po 5 s zamiast zawieszenia. Bez `DATABASE_URL` (np. STG) testy bazy są pomijane, a nie kończą się błędem.
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-011: CI w repo testów od Etapu 2, bez Dockera
- **Data:** 2026-11-06
- **Kontekst:** pierwotny plan dawał CI dopiero w Etapie 5. Repo jest publiczne od Etapu 2, a krótka pętla informacji zwrotnej od pierwszego commita to dobra praktyka.
- **Rozważane opcje:**
  - A — CI dopiero w Etapie 5 — zgodnie z planem, ale błędy lintera i testów frameworka wychodzą późno
  - B — od razu pełne CI z Dockerem — wymaga tokenu do prywatnego repo sklepu i minut na build obrazu
  - C — teraz tylko ruff i testy frameworka (`tests/framework`), bez Dockera i sekretów
- **Decyzja:** C. Workflow `.github/workflows/ci.yml` na push i PR do `main`.
- **Konsekwencje:** przebieg trwa kilkadziesiąt sekund i nie potrzebuje sekretów. Testy smoke na sklepie dalej uruchamia się lokalnie; Docker w CI i bramka na PR sklepu zostają w Etapie 5 (ADR-005).
- **Na rozmowie:** <!-- do uzupełnienia -->

### ADR-012: Własny produkt na test
- **Data:** 2026-11-13
- **Kontekst:** kilkanaście testów składa zamówienie, a każde zamówienie zdejmuje stan magazynowy. Seed ma po 5 sztuk na rozmiar, jeszcze się zmieni i nie ma produktu z procentem promocji. Zamówień nie da się usunąć przez API.
- **Rozważane opcje:**
  - A — fixture wstawia SQL-em własny produkt (`test-<hex>`, własny stan, cena, promocja) i po teście usuwa go razem z jego zamówieniami i opiniami
  - B — testy zamawiają różne rozmiary i produkty z seeda — działa tylko na świeżej bazie, psuje się przy zmianie seeda, nie da się sprawdzić promocji
  - C — sprzątanie oddaje stan (anulowanie zamówienia albo `UPDATE`) — test zmienia rekord seeda, czyli łamie zasadę „ruszamy tylko własne dane”
- **Decyzja:** A (decyzja właściciela projektu). Fixtures `make_product`, `product`, `placed_order`. Seed jest tylko czytany: wyszukiwarka, opinie CASTELLO, strona produktu.
- **Konsekwencje:** testy przechodzą wielokrotnie bez `down -v`, nie zależą od seeda i są gotowe na równoległość. Koszt: wstawianie przez SQL trzeba poprawić, gdy sklep doda wymaganą kolumnę do `ProductRow` (pilnuje tego osobny test), a testy zamówień wymagają `DATABASE_URL`, więc na STG są dziś pomijane. Funkcja sprzątająca odmawia usunięcia sluga bez prefiksu `test-`. Zamyka otwartą decyzję o stanie magazynowym i doprecyzowuje ADR-003.
- **Na rozmowie:** Każdy test, który coś kupuje, dostaje własny produkt z własnym stanem i sam po sobie sprząta. Dzięki temu testy nie psują sobie danych, można je uruchamiać wiele razy i równolegle, a zmiana danych startowych ich nie rusza.

### ADR-013: Oczekiwany wynik z reguł biznesowych, asercje względem stanu sprzed akcji
- **Data:** 2026-11-13
- **Kontekst:** scenariusze powstały z czytania kodu sklepu. Test napisany „pod kod” zatwierdza także jego błędy. Dane startowe (seed) będą się zmieniać.
- **Rozważane opcje:**
  - A — oczekiwane wartości spisane z tego, co sklep akurat zwraca, i liczby z seeda na sztywno („5 sztuk”)
  - B — oczekiwane wartości z reguł potwierdzonych przez właściciela sklepu; test porównuje stan po akcji ze stanem sprzed akcji („spadł o 2”)
- **Decyzja:** B. Reguły (R1–R24) są w macierzy śledzenia, każda ze źródłem. Rozbieżność między regułą a sklepem to znalezisko do zgłoszenia, a nie powód do zmiany testu.
- **Konsekwencje:** test czerwony oznacza złamaną regułę, a nie zmianę danych. Koszt: reguły trzeba spisać i potwierdzić, zanim powstanie test.
- **Na rozmowie:** Oczekiwany wynik biorę z wymagań, nie z kodu, bo inaczej test potwierdza także błędy. Nie wpisuję na sztywno liczb z danych startowych, tylko sprawdzam różnicę przed i po akcji.

### ADR-014: Testy zachowań czekających na zmianę w sklepie nie trafiają do publicznego repo przed tą zmianą
- **Data:** 2026-11-13
- **Kontekst:** repo testów jest publiczne. Część scenariuszy dotyczy zachowań, które sklep ma dopiero poprawić. Test oznaczony `xfail` z opisem byłby publiczną informacją o otwartej słabości.
- **Rozważane opcje:**
  - A — wszystkie testy od razu, nieprzechodzące oznaczone `xfail` z powodem
  - B — dwa kroki: krok A to testy zachowań, które sklep ma poprawnie; krok B to pozostałe testy, pisane po zmianie w sklepie
- **Decyzja:** B. Lista zgłoszeń i notatka dla repo sklepu zostają lokalnie (wykluczone z gita) do czasu naprawy.
- **Konsekwencje:** publiczne repo jest zawsze zielone i nie opisuje otwartych słabości. Koszt: testy kroku B powstają później, a do tego czasu macierz ich nie pokazuje.
- **Na rozmowie:** Znalezionych słabości nie publikuję przed naprawą. Zgłaszam je właścicielowi aplikacji, a test dodaję do publicznego repo dopiero wtedy, gdy poprawka jest wdrożona.

### ADR-015: Równoległość `-n 4` w `addopts`, nie w poleceniu
- **Data:** 2026-11-16
- **Kontekst:** po Etapie 3 testy mają własne dane, więc można je uruchamiać równolegle. Trzeba było zdecydować, gdzie ustawić liczbę procesów.
- **Rozważane opcje:**
  - A — jawnie w poleceniu (`-n 4`): zwykłe `pytest` zostaje jednoprocesowe, ale łatwo zapomnieć o fladze
  - B — `-n 4` w `addopts`: każdy przebieg równoległy bez myślenia; debugowanie (`--pdb`) i podgląd (`--headed`) wymagają `-n 0`
  - C — zmienna `WORKERS` w `.env` czytana przez hook przed fixturami: wygodne lokalnie, ale więcej kodu na prosty cel
- **Decyzja:** B (decyzja właściciela projektu), 4 procesy, dystrybucja domyślna (`load`), E2E też równolegle. Wyjątek: w CI testy frameworka idą z `-n 0`, bo pomiar dał 0,5 s wobec 4,8 s.
- **Konsekwencje:** zielone 3 przebiegi z rzędu bez kolizji i bez śladów w bazie. Czas całości bez zmian (ok. 15 s), więc zysk to dowód niezależności, a nie szybkość. Czy przy większym zestawie się opłaci, trzeba będzie zmierzyć. Koszt: do podglądu przeglądarki i debugowania trzeba pamiętać o `-n 0`; `--pdb` zgłasza to błędem, a `-s` po cichu nie wypisuje nic. `pytest-xdist` jest w grupie `dev`, więc `uv sync --no-dev` i `pytest` zakończą się błędem „unrecognized arguments: -n” (CI robi `uv sync --locked` z grupą `dev`). Test `test_pytest_config.py` pilnuje konfiguracji. Marker `serial` i `loadfile` nie były potrzebne; wprowadzamy je dopiero z uzasadnieniem.
- **Na rozmowie:** Testy uruchamiam domyślnie na czterech procesach, bo to dobry sposób, żeby wykryć testy zależne od siebie, a każdy przebieg sprawdza to samo bez dodatkowej flagi. U mnie nic się nie wywróciło, bo każdy test ma własne dane, ale mierzyłem też czas i przy tak małym zestawie przyspieszenia nie ma. Do debugowania wyłączam równoległość jednym przełącznikiem.

### ADR-016: Bramka testów na PR sklepu: workflow w repo sklepu, publiczne testy bez tokena, bramka informacyjna na darmowym planie
- **Data:** 2026-11-17
- **Kontekst:** zmiany w sklepie trafiały na `main` i od razu na Vercel, a testy uruchamiało się ręcznie. Chcemy wykryć błąd przed scaleniem. Sklep jest prywatny, repo testów publiczne.
- **Rozważane opcje:**
  - A — workflow w repo sklepu pobiera repo testów (checkout) i raportuje status do PR-a sklepu
  - B — `repository_dispatch` z repo sklepu do repo testów: wynik nie wraca do PR-a automatycznie
  - Gałąź testów: zawsze `main` (A1) albo gałąź o tej samej nazwie co gałąź PR-a, a gdy jej nie ma `main` (A2), albo ręczny parametr (A3)
  - Egzekwowanie: reguła ochrony na GitHubie (wymaga płatnego planu w prywatnym repo), bramka na wdrożeniu (5B) albo upublicznienie repo sklepu (odrzucone: prywatny kod i materiały sklepu)
- **Decyzja:** A z A2. Workflow `tests` w repo sklepu, checkout publicznego repo testów **bez tokena**, wybór gałęzi przez `git ls-remote` (nazwa gałęzi przekazywana tylko przez zmienną środowiskową, nigdy do skryptu przez `${{ }}`), obraz sklepu budowany przy każdym przebiegu bez cache (191 s), do 3 prób budowy przy chwilowym błędzie sieci. **Bramka jest informacyjna** (decyzja właściciela): reguła ochrony jest zapisana, ale nieegzekwowana na darmowym planie; zostają zasady w `AGENTS.md` i scalanie przez człowieka.
- **Konsekwencje:** błąd w sklepie widać przy PR-ze po ok. 4 minutach, razem z logami i śladami. Zmiana zachowania sklepu i testów idzie parą gałęzi o tej samej nazwie; gałąź testów musi istnieć przed startem przebiegu, a oba PR-y scala się razem (sklep, zaraz po nim testy), bo inaczej kolejne PR-y sklepu są czerwone. Koszt: czerwony status nie blokuje Merge ani pushu na `main`, więc ochrona zależy od dyscypliny. Wrócić do tematu w 5B (bramka na wdrożeniu) albo po zakupie planu Pro. Budowa obrazu to 80% czasu przebiegu, więc w kolejnym kroku warto użyć cache albo gotowego obrazu.
- **Na rozmowie:** Każdy pull request w sklepie buduje go w Dockerze i uruchamia moje testy, a wynik widać przy PR-ze. Sprawdziłem też, że bramka umie być czerwona, celowo psując cenę. Na darmowym planie GitHuba ta bramka tylko ostrzega, a nie blokuje, więc egzekwowanie dołożę na wdrożeniu albo przez płatny plan.

<!--
### ADR-001: <tytuł decyzji>
- **Data:**
- **Kontekst:** jaki problem rozwiązuję
- **Rozważane opcje:**
  - A — plusy / minusy
  - B — plusy / minusy
- **Decyzja:** co wybrałem
- **Konsekwencje:** co zyskuję, co tracę, kiedy wrócić do tematu
- **Na rozmowie:** jak to wytłumaczyć w 2–3 zdaniach
-->

---

## 5. Najlepsze praktyki

Format: **zasada → dlaczego → przykład z mojego kodu**.

### Struktura i nazewnictwo testów
### Izolacja testów i dane testowe
### Stabilność (selektory, oczekiwania, flaky tests)
### Konfiguracja i środowiska (env, secrets)
### Logowanie i raportowanie
### Jakość kodu frameworka (typing, linting, review)

---

## 6. Problemy i rozwiązania

<!--
### <krótki opis problemu>
- **Objaw:**
- **Przyczyna:**
- **Rozwiązanie:**
- **Jak zapobiec:**
- **Na rozmowie:** dobra historia do pytania „opowiedz o trudnym problemie”
-->

### Silnik Dockera odpowiada błędem 500 po starcie (Etap 3, 2026-11-13)
- **Objaw:** `docker compose ps` wisi ponad 2 minuty. `docker version` zwraca `request returned Internal Server Error for API route`, a chwilę wcześniej `open //./pipe/docker_engine: The system cannot find the file specified`. Sklep pod `127.0.0.1:3100` nie odpowiada.
- **Przyczyna:** Docker Desktop był w trakcie startu albo jego silnik się zawiesił. Procesy Docker Desktop działały, ale silnik nie przyjmował poleceń.
- **Rozwiązanie:** restart Docker Desktop, potem `docker compose up -d --build --wait`.
- **Jak zapobiec:** przed pracą sprawdzić `docker version` (ma pokazać wersję serwera). Polecenia Dockera w skryptach uruchamiać z limitem czasu, żeby zawieszony silnik dawał błąd, a nie czekanie.
- **Na rozmowie:** Gdy środowisko nie odpowiada, najpierw sprawdzam, czy działa sam silnik Dockera, a dopiero potem szukam błędu w aplikacji. Nie restartuję cudzych kontenerów bez pytania, bo restart silnika zatrzymuje wszystko.

### Testy zamówień wyczerpują stan magazynowy seeda (Etap 3, 2026-11-13)
- **Objaw:** wykryte przy przeglądzie projektu, przed napisaniem testów: kilkanaście scenariuszy zamawia ten sam produkt z seeda, który ma 5 sztuk na rozmiar. Drugi przebieg bez `down -v` byłby czerwony. Test ceny promocyjnej nie miał na czym działać, bo żaden produkt seeda nie ma procentu promocji.
- **Przyczyna:** projekt odkładał własne dane testu do Etapu 4, a testy zmieniające dane powstawały już w Etapie 3.
- **Rozwiązanie:** własny produkt na test (ADR-012), przeniesiony z Etapu 4 do Etapu 3.
- **Jak zapobiec:** przy projektowaniu testów od razu pytać, które z nich zmieniają dane i ile razy mogą się wykonać na tej samej bazie. Niezależny przegląd projektu przed planem wyłapał to, zanim powstał kod.
- **Na rozmowie:** Zanim napisałem testy zamówień, policzyłem, ile razy zdejmą stan magazynowy. Wyszło, że dane startowe skończą się w pierwszym przebiegu, więc każdy test dostał własny produkt.

### `next build` w Dockerze pada, choć commit wyglądał na gotowy (Etap 1, 2026-11-04)
- **Objaw:** `docker compose up --build` kończy się błędem `PrismaClientInitializationError` przy prerenderze `/blog`. Na Vercelu ten sam kod buduje się bez problemu.
- **Przyczyna:** Vercel ma bazę w czasie builda, a `docker build` nie. Agent sklepu nie mógł uruchomić builda, bo Docker był zawieszony, więc kryterium akceptacji nie zostało sprawdzone. Przegląd samego diffa też tego nie wyłapał.
- **Rozwiązanie:** ADR-007, `force-dynamic` na `/blog` i `/szycie-na-miare`.
- **Jak zapobiec:** kryterium „build przechodzi” wymaga dowodu z uruchomienia; czytanie kodu go nie zastępuje. Zmianę sprawdzać też zachowaniem: znacznik wstawiony w SQL pokazał, które strony naprawdę czytają bazę.
- **Na rozmowie:** <!-- do uzupełnienia -->

### Pierwszy przebieg CI pada na „Set up job” (Etap 2, 2026-11-06)
- **Objaw:** `Unable to resolve action astral-sh/setup-uv@v10, unable to find version v10`.
- **Przyczyna:** `setup-uv` publikuje tylko pełne wersje (`v10.3.3`), bez ruchomego tagu głównej wersji, w przeciwieństwie do `actions/checkout@v7`. Sprawdziłem najnowsze wydanie, ale nie to, czy istnieje tag `v10`.
- **Rozwiązanie:** `astral-sh/setup-uv@v10.3.3`.
- **Jak zapobiec:** przed użyciem akcji sprawdzić tag, a nie tylko wydanie (`gh api repos/<owner>/<repo>/git/ref/tags/<tag>`). Pełna wersja albo SHA commita to też bezpieczniejsza praktyka.
- **Na rozmowie:** <!-- do uzupełnienia -->

### Każde połączenie z Dockerem trwa kilka sekund (Etap 2, 2026-11-06)
- **Objaw:** test bazy przechodził, ale trwał 5,0 s, dokładnie tyle, ile `connect_timeout`; test API ok. 2 s.
- **Przyczyna:** na Windows `localhost` rozwiązuje się najpierw na IPv6 `::1`, a porty compose są wystawione tylko na `127.0.0.1` (Etap 1). Każde połączenie czekało do timeoutu na `::1`, a dopiero potem szło po IPv4. Pomiar: `localhost` 5,04 s, `127.0.0.1` 0,02 s.
- **Rozwiązanie:** w `.env` i `.env.example` adresy `127.0.0.1` zamiast `localhost`. Zestaw z ok. 7 s spadł do 0,06 s.
- **Jak zapobiec:** test, który „przechodzi, ale wolno”, to sygnał. Czas równy wartości timeoutu prawie zawsze oznacza, że coś na niego czeka.
- **Na rozmowie:** <!-- do uzupełnienia -->

### Vitest daje inny wynik u agenta AI (Etap 1, 2026-11-05)
- **Objaw:** u Groka 74/74, u Claude Code 1 plik padł i 30 testów pominięto.
- **Przyczyna:** `own-commerce.test.ts` uruchamia `prisma db push --force-reset`, a Prisma odmawia takich komend, gdy wykryje wywołanie przez Claude Code. Blokada działa zależnie od tego, kto uruchamia test. Reset dotyczy tylko lokalnego `prisma/prisma/test.db`.
- **Rozwiązanie:** blokady nie obchodzimy; wynik pełnego przebiegu pochodzi od Groka, a przyczynę potwierdzono w kodzie testu i po czasie modyfikacji pliku.
- **Jak zapobiec:** przy rozbieżnych wynikach szukać różnicy w środowisku, zanim uzna się test za zepsuty. Przed uruchomieniem cudzych testów sprawdzić, czy resetują bazę i którą.

### Docker zawiesza się w trakcie buildu (Etap 1, 2026-11-04)
- **Objaw:** `docker compose up --build` stoi ponad godzinę na `npm ci`, potem każda komenda `docker` zwraca `Internal Server Error ... docker_engine`. Restart Docker Desktop pomaga tylko na chwilę.
- **Przyczyna:** pełny dysk C: (79 MB wolnego). Docker Desktop trzyma wszystko w jednym pliku `AppData\Local\Docker\wsl\data\ext4.vhdx` (31,4 GB), który **rośnie, ale sam się nie kurczy** — w środku było tylko ~9 GB danych (stare obrazy, 5,4 GB cache budowania), reszta to miejsce po dawno usuniętych warstwach.
- **Rozwiązanie:** `npm cache clean --force` (+5 GB); usunięcie starych obrazów i kontenerów + `docker builder prune -a`; zamknięcie Docker Desktop, `wsl --shutdown` i kompaktowanie w `diskpart` (`select vdisk file=...`, `attach vdisk readonly`, `compact vdisk`, `detach vdisk`) → vhdx 31,4 → 10,5 GB, wolne 24,4 GB.
- **Jak zapobiec:** przed buildem `docker system df` i wolne miejsce na dysku (build Next.js potrzebuje ~8–10 GB); okresowo `docker builder prune`; kompaktowanie vhdx po dużych porządkach; ewentualnie przeniesienie dysku Dockera na inny dysk (Settings → Resources → Disk image location). Diagnoza zaczyna się od zasobów (dysk, RAM), nie od restartu.
- **Przy okazji — lekcja o `.dockerignore`:** stary obraz frameworka z poprzedniej pracy miał warstwę `COPY . /test_root` = 606 MB, bo bez `.dockerignore` trafiło do niego całe repo: `.git`, `.idea`, logi, pobrane pliki i plik z danymi logowania. Obraz można skopiować, wypchnąć do rejestru i rozpakować — wszystko, co w nim jest, trzeba traktować jak opublikowane. Dlatego w Dockerfile sklepu jest `.dockerignore` (`.env*`, `.git`, `node_modules`, `*.db`).
- **Na rozmowie:** historia „opowiedz o trudnym problemie”: objaw wyglądał na awarię Dockera, a przyczyną były zasoby hosta; najpierw zmierzyłem (dysk, `docker system df`, rozmiar vhdx), dopiero potem sprzątałem — i tylko za zgodą właściciela danych.

### Push odrzucony: „email privacy restrictions” (Etap 5A, 2026-11-17)
- **Objaw:** `git push` do repo sklepu kończy się `push declined due to email privacy restrictions`, a `gh pr create` zgłasza „No commits between main and branch”.
- **Przyczyna:** repo sklepu miało w konfiguracji prywatny adres e-mail autora, a konto ma włączone blokowanie pushy ujawniających adres. Repo testów używało adresu `noreply` od początku, więc tam problemu nie było.
- **Rozwiązanie:** przepisanie autora jednego, jeszcze niewypchniętego commita na adres `noreply` (`git -c user.email=... commit --amend --reset-author`), bez zmiany konfiguracji repo.
- **Jak zapobiec:** w każdym repo ustawić `user.email` na adres `<id>+<login>@users.noreply.github.com` (w repo sklepu zrobi to właściciel, bo to jego konfiguracja).
- **Na rozmowie:** GitHub odrzucił push, bo w commicie był mój prywatny adres. Naprawiłem tylko ten commit adresem `noreply` i dodałem w notatkach, żeby ustawić go w każdym repo.

### Bramka czerwona przez chwilowy błąd sieci (Etap 5A, 2026-11-17)
- **Objaw:** drugi przebieg tego samego PR-a padł w budowie obrazu: `npm ci ... ECONNRESET`, mimo że pierwszy był zielony.
- **Przyczyna:** chwilowy błąd połączenia z rejestrem npm na runnerze, niezwiązany ze zmianą.
- **Rozwiązanie:** pętla do 3 prób wokół `docker compose up --build --wait` (z `down -v` między próbami). Przetestowana na atrapie: sukces od razu, sukces po ponowieniu i trwała porażka (kod 1).
- **Jak zapobiec:** kroki zależne od sieci (pobieranie paczek, obrazów) powtarzać. Koszt: prawdziwy błąd budowy też jest powtarzany trzy razy, więc czerwony pojawia się później.
- **Na rozmowie:** Bramka, która czasem jest czerwona bez powodu, uczy ludzi ją ignorować. Przy błędzie sieci w budowie ponawiam krok do trzech razy, a testów nie ponawiam, żeby nie ukrywać prawdziwych porażek.

### Reguła ochrony zapisana, ale nieegzekwowana (Etap 5A, 2026-11-17)
- **Objaw:** po zapisaniu reguły dla `main` sklepu GitHub pokazał, że nie będzie egzekwowana w tym prywatnym repo. API: `protected: false`, endpointy reguł zwracają 403 „Upgrade to GitHub Pro or make this repository public”.
- **Przyczyna:** ochrona gałęzi w prywatnych repo wymaga płatnego planu. Założyłem, że wystarczy plan darmowy, bo tak działa w publicznym repo testów, i tego nie sprawdziłem przed budową.
- **Rozwiązanie:** decyzja właściciela: bramka informacyjna (czerwony status widać, ale Merge nie jest blokowany), zasady w `AGENTS.md`, egzekwowanie w 5B (bramka na wdrożeniu) albo po zakupie planu Pro. Nie sprawdzałem tego próbnym pushem na `main`, bo push deployuje na Vercel.
- **Jak zapobiec:** przed zaplanowaniem bramki sprawdzić, co plan konta pozwala egzekwować (`gh api repos/<repo>/branches/main/protection`).
- **Na rozmowie:** Okazało się, że na darmowym planie GitHub nie egzekwuje reguł ochrony w prywatnym repo. Zamiast to ukrywać, opisałem to jako ograniczenie bramki i zaplanowałem egzekwowanie na wdrożeniu.

### Testy równolegle nie są szybsze (Etap 4, 2026-11-16)
- **Objaw:** `-n 4` daje ten sam czas co jeden proces (ok. 15 s), E2E nawet wolniej (6,3 → 8,0 s), a zestaw frameworka ok. 8–9 razy wolniej (0,5 → 4,8 s).
- **Przyczyna:** każdy z 4 procesów startuje osobno (import, kolekcja testów, własna przeglądarka w E2E), a większość testów trwa ułamek sekundy. Czy sklep (jeden proces Node w Dockerze) jest dodatkowym ograniczeniem, nie sprawdzałem: API przyspieszyło (5,3 → 4,4 s), więc nie wygląda na główną przyczynę.
- **Rozwiązanie:** zostawiony `-n 4` jako dowód niezależności testów, w CI testy frameworka z `-n 0`. Ocena zysku czasu odłożona do chwili, gdy zestaw urośnie (Etap 5, sklep w CI).
- **Jak zapobiec:** przed ogłoszeniem przyspieszenia zmierzyć czas z równoległością i bez niej, osobno dla każdego poziomu.
- **Na rozmowie:** Zmierzyłem czas na jednym i na czterech procesach i przy 150 krótkich testach różnicy nie było, bo start procesów zjadał zysk. Dlatego równoległość traktuję najpierw jako sprawdzian niezależności testów, a dopiero potem jako przyspieszenie.

---

## 7. Zarządzanie frameworkiem

- **Wersjonowanie:** <!-- SemVer, changelog -->
- **Proces zmian:** <!-- branching, PR, code review -->
- **Użycie przez innych:** <!-- onboarding, dokumentacja, konwencje -->
- **Metryki zdrowia:** <!-- czas wykonania, % flaky, liczba testów, pokrycie -->

### Macierz śledzenia wymagań (traceability matrix)

Łączy trzy rzeczy: wymaganie (reguła sklepu, `R…`) → przypadek testowy (ID, np. `A-CART-03`) → test automatyczny (plik i funkcja pytest). Wynik: [`docs/traceability-matrix.pdf`](docs/traceability-matrix.pdf). Wprowadzona 2026-11-13.

**Trzy części mechanizmu**

| Część | Plik | Rola |
|---|---|---|
| Dane | `docs/traceability.json` | jedyne miejsce edytowane ręcznie: lista wymagań i lista przypadków |
| Budowanie PDF | `scripts/build_traceability.py` (logika w `src/jersa/traceability.py`) | czyta dane i generuje PDF; przy niespójnych danych nic nie zapisuje |
| Strażnik | `tests/framework/test_traceability.py` | w CI sprawdza, czy każdy przypadek ma istniejące wymaganie, czy ID się nie powtarzają i czy każdy przypadek `zautomatyzowany` ma funkcję testu w kodzie |

**Jak dodać nowy test (trzy kroki)**

1. **Kod testu** w katalogu według poziomu: `tests/contract/`, `tests/api/`, `tests/db/` albo `tests/e2e/`. Docstring zaczyna się od ID przypadku:
   ```python
   def test_removing_all_lines_empties_cart(shop, product):
       """A-CART-14: usunięcie wszystkich pozycji zostawia pusty koszyk."""
   ```
2. **Wpis w `docs/traceability.json`**, na liście `cases`, obok przypadków z tej samej grupy:
   ```json
   {"id": "A-CART-14", "level": "API", "reqs": ["R10"], "status": "zautomatyzowany",
    "title": "Usunięcie wszystkich pozycji zostawia pusty koszyk",
    "tests": ["tests/api/test_cart.py::test_removing_all_lines_empties_cart"]}
   ```
   `id` to kolejny wolny numer w grupie, `reqs` to reguły, które test sprawdza, `tests` to ścieżka i nazwa funkcji dokładnie jak w kodzie. Pole `smoke: true` tylko dla testów z markerem `smoke`.
3. **Przebudowa PDF:** `uv run python scripts/build_traceability.py`.

**Inne sytuacje**

| Sytuacja | Co zrobić |
|---|---|
| Zmiana nazwy albo usunięcie testu | poprawić pole `tests` (albo usunąć przypadek) w tym samym commicie; inaczej CI jest czerwone |
| Nowa reguła sklepu | dopisać wymaganie do listy `requirements`; w PDF pojawi się „LUKA”, dopóki nie ma do niej przypadku |
| Przypadek zaplanowany, testu jeszcze nie ma | status `zaplanowany`; strażnik go nie sprawdza |
| Test napisany | status `zautomatyzowany` |

Po każdej zmianie danych: przebudować PDF i zacommitować go razem z JSON-em.

**Czego mechanizm nie robi sam**

- Nie przebudowuje PDF automatycznie: bez uruchomienia skryptu PDF pokazuje stary stan.
- Nie wykrywa testu, którego nie wpisano do JSON-a: strażnik pilnuje tylko tego, co jest w danych.
- Nie ocenia jakości testu: pokazuje, że test istnieje, a nie, że jest dobry.

Plików `scripts/build_traceability.py` i `src/jersa/traceability.py` przy dodawaniu testów się nie zmienia: to mechanizm, nie dane.

---

## 8. Kroki wdrożenia (1 → n)

> Kolejne istotne kroki przy budowie frameworka, w kolejności wykonania — mapa do zbudowania kolejnego frameworka od zera.
> Format: **krok** — jedno zdanie: co i po co. Dopisywane na bieżąco.

1. **Określ cel i zakres** — po co framework, co testuje, czego świadomie nie robi.
2. **Poznaj system testowany** — stack, endpointy, baza, hosting, istniejące testy.
3. **Ustal poziomy testów** — piramida: kontrakt, API, DB, E2E; co sprawdza każdy poziom.
4. **Zapisz kluczowe decyzje jako ADR** — wybór języka/repo, strategia kontraktów, danych i CI.
5. **Zidentyfikuj ryzyka** — co może zablokować projekt i jak temu zapobiec.
6. **Rozpisz etapy wdrożenia** — kolejność prac z mierzalnym wynikiem każdego etapu.
7. **Przygotuj dokumentację projektu** — `CLAUDE.md` (kontekst i konwencje) + `KNOWLEDGE.md` (wiedza).
8. **Rozpoznaj konfigurację SUT** — jak system wybiera bazę, tryby i zmienne środowiskowe, żeby postawić go powtarzalnie do testów.
9. **Wyznacz granice kontraktu API** — co jest prawdziwym API (JSON), a co tylko renderowanym UI; stan sesji (cookies) i format błędów.
10. **Spisz referencję API i dane testowe** — endpointy z przykładowymi odpowiedziami i znany seed; to materiał na schematy kontraktów i stabilny happy path.
11. **Znajdź współdzielone zasoby** — co testy zmieniają globalnie (np. stan magazynowy) i jak to przywracać, zanim włączysz równoległość.
12. **Zaprojektuj środowiska testowe** — gdzie działa SUT (Docker / staging), gdzie działają testy, jak są wystawione adresy i jak przełączać cel (`BASE_URL`).
13. **Zmapuj środowiska na potrzeby projektu** — które z DEV/INT/STG/PROD są naprawdę potrzebne; środowiska tymczasowe w CI mogą zastąpić INT przy małym systemie.
14. **Zaplanuj wyzwalacze CI** — co, kiedy i na jakiej wersji SUT; najważniejsza jest bramka na PR aplikacji, żeby błąd nie dotarł na staging.
15. **Zainicjalizuj repo i zrób pierwszy commit przed kodem** — `.gitignore` od startu (`.env`, raporty, cache), żeby sekrety i artefakty nigdy nie trafiły do historii.
16. **Zamów obraz aplikacji u jej właściciela** — Dockerfile przy kodzie aplikacji, compose przy testach; wymagania przekazane notką z kryteriami akceptacji, a stałe zasady zapisane w instrukcjach repo aplikacji.
17. **Oddziel budowanie obrazu od danych** — obraz nie powinien wymagać bazy do zbudowania, a kryterium „build przechodzi” wymaga dowodu z uruchomienia.
18. **Sprawdź środowisko zachowaniem, nie tylko statusem** — healthy nie dowodzi, że strony czytają bazę; znacznik w SQL i świeży seed po `down -v` już tak.
19. **Po każdej zmianie aplikacji porównaj środowiska** — ta sama odpowiedź API na DEV i STG pokazuje, czy różnią się kodem, czy danymi; różnica w danych mówi, czego testy na STG nie mogą zakładać.
20. **Przejrzyj poprzedni framework przed nowym szkieletem** — lista błędów z dawnego `conftest.py` (globalny stan, zbyt szerokie sprzątanie, brak `assert`) to gotowe wymagania dla nowego.
21. **Zbuduj szkielet z jednym testem na każdy poziom** — kontrakt, API, DB i E2E po jednym teście dowodzą, że każda fixture działa, zanim dojdą dziesiątki scenariuszy.
22. **Testuj sam framework bez aplikacji** — loader schematów, konfiguracja i klienci mają własne szybkie testy, które CI uruchamia bez Dockera.
23. **Włącz CI od pierwszego pushu** — nawet sam linter i testy frameworka dają informację zwrotną przy każdym commicie.
24. **Przed upublicznieniem repo przeskanuj całą historię** — dane osobowe i sekrety z dowolnego commita da się usunąć tylko przed pierwszym pushem (`git filter-repo`).
25. **Spisz reguły biznesowe i daj je do potwierdzenia właścicielowi aplikacji** — oczekiwany wynik testu ma pochodzić z wymagań, nie z kodu, który może mieć błąd.
26. **Sprawdź podejrzenia uruchomieniem, zanim je zgłosisz** — błąd odczytany z kodu to hipoteza; zgłoszenie ma zawierać to, co aplikacja zrobiła naprawdę, i to, co ma robić.
27. **Nie publikuj otwartych słabości** — testy i opisy zachowań czekających na poprawkę zostają lokalnie do czasu naprawy.
28. **Połącz wymagania, przypadki i testy macierzą śledzenia** — widać luki w pokryciu, a przy zmianie reguły wiadomo, które testy ruszyć.
29. **Daj każdemu testowi zmieniającemu dane własne dane** — własny produkt wstawiany przez fixture i usuwany po teście, żeby testy były powtarzalne i niezależne od seeda.
30. **Dokładaj testy od dołu piramidy** — najpierw kontrakt i API, potem baza, na końcu kilka ścieżek E2E na gotowych fixtures.
31. **Zobacz każdy nowy test na czerwono** — celowo zmieniona oczekiwana wartość dowodzi, że test umie wykryć błąd i że komunikat jest czytelny.
32. **Uruchom cały zestaw kilka razy z rzędu i sprawdź ślady w bazie** — powtarzalność i sprzątanie potwierdza się pomiarem, nie założeniem.
33. **Włącz równoległość (`-n 4`) i sprawdź, czy testy są niezależne** — pytest-xdist w `addopts`, test pilnujący konfiguracji, trzy przebiegi z kontrolą bazy (ADR-015).
34. **Zmierz czas z równoległością i bez niej, osobno dla każdego poziomu** — krótki zestaw nie przyspiesza, a start procesów może go spowolnić; tam, gdzie tak jest, wyłącz `-n` (`ci.yml`: `-n 0`).
35. **Postaw bramkę tam, gdzie powstaje zmiana** — workflow w repo sklepu uruchamia testy z osobnego repo na każdym PR-ze; sam plik YAML to zapalnik, a reguła ochrony to osobne ustawienie w GitHubie (ADR-016).
36. **Zobacz bramkę na czerwono** — celowo zepsuta zmiana w tymczasowym PR-ze, zamkniętym bez scalania, dowodzi, że status umie być czerwony i że komunikat wskazuje regułę.
37. **Sprawdź, co plan konta pozwala egzekwować, zanim zbudujesz bramkę** — reguła ochrony w prywatnym repo na darmowym planie jest zapisana, ale nieegzekwowana.

---

## 9. Przygotowanie do rozmów (SDET)

Pytania, które mogą paść, i odpowiedź oparta na **moim** frameworku (z linkiem do ADR / problemu).

### Jak zapewniasz powtarzalne środowisko testowe?
- **Odpowiedź:** konteneryzuję SUT (Docker + docker-compose): sklep i Postgres startują jedną komendą, z czystą bazą i znanym seedem po `down -v`, a w CI na każdy przebieg. Działa lokalnie; ten sam układ działa w CI na PR-ach sklepu (Etap 5A) i jest zaplanowany w chmurze (Etap 6). Testy nie zależą od współdzielonego stagingu ani od tego, co ktoś wcześniej kliknął, i idą na tym samym silniku bazy co produkcja (Postgres, nie SQLite).
- **Czego unikam:** „u mnie działa”, testów na współdzielonym stagingu ze zmiennymi danymi, różnic między bazą testową a produkcyjną.
- **Dowód:** Etap 1 (Docker), notatki z Etapu 0 (Prisma SQLite ↔ Postgres), sekcja 10 — SUT, seed.

### Czy środowisko INT jest zawsze potrzebne?
- **Odpowiedź:** nie zawsze — zależy od liczby serwisów i integracji. Część roli INT (sprawdzenie, czy nowy kod jednej aplikacji działa) przejmują środowiska tymczasowe w CI: szybciej (na każdy push, nie raz na noc), bez kolejki i bez zabrudzonych danych. To podejście shift-left. INT nadal ma sens przy wielu serwisach różnych zespołów, prawdziwych integracjach zewnętrznych, testowaniu procesu wdrożenia i migracji na trwałej bazie. Między serwisami część jego roli mogą przejąć testy kontraktowe.
- **Przykład z mojego projektu:** w jersa Docker w CI pełni rolę INT, bo to jedna aplikacja z mockowanym PayU; po wydzieleniu backendu (Etap 8) wróciłbym do wspólnego środowiska integracyjnego lub Pact.
- **Dowód:** sekcja 3 — mapowanie środowisk.

### Czym różni się Docker od CI?
- **Odpowiedź:** Docker to sposób pakowania i uruchamiania aplikacji (*jak* postawić środowisko); CI to automat uruchamiający kroki po zdarzeniu (*kiedy* i *co* uruchomić). Są niezależne: Docker działa bez CI na laptopie, CI może działać bez Dockera. Razem dają to samo środowisko lokalnie i w pipeline — jeśli działa u mnie w Dockerze, prawie na pewno zadziała w CI.
- **Dowód:** sekcja 3 — środowisko testowe; Etapy 1 i 5.

### Jak wygląda Twój pipeline CI i kiedy uruchamiasz testy?
- **Odpowiedź:** cztery wyzwalacze, każdy z innym celem. Główny to bramka na PR aplikacji: runner stawia sklep z gałęzi PR-a w Dockerze z czystą bazą, odpala pełny zestaw (kontrakt, API, DB, E2E), a czerwony wynik blokuje merge — błąd nie trafia na staging. Przy zmianie w samych testach uruchamiam je na `main` aplikacji, żeby zmieniała się tylko jedna rzecz. Na stagingu: nightly regression i smoke po każdym deployu. Artefakty: raport HTML, trace i wideo Playwrighta przy porażce.
- **Pułapki, które znam:** wywołania między repo wymagają PAT/GitHub App; cron chodzi w UTC; budowa obrazu kosztuje minuty (cache / gotowy obraz z rejestru).
- **Dowód:** ADR-005, sekcja 3 — CI.

### Co to jest shift-left i jak go stosujesz?
- **Odpowiedź:** przesuwanie testów jak najwcześniej w procesie, bo im wcześniej wykryty błąd, tym tańsza naprawa. To nie jeden krok, tylko cała oś: review wymagań → testy jednostkowe → testy lokalnie przed pushem → bramka na PR → staging → produkcja. U mnie konkretnie: przeniosłem testowanie zmian aplikacji z „po deployu na staging” na „przed merge” (bramka na PR) — to przesunięcie w lewo, ale nie pełny shift-left; wcześniej są jeszcze testy jednostkowe (Vitest) i uruchamianie testów lokalnie w Dockerze.
- **Dowód:** ADR-005, sekcja 10 — shift-left.

### Jak wygląda Twoja codzienna praca z testami lokalnie?
- **Odpowiedź:** rano raz `docker compose up -d --build --wait` — compose buduje obraz aplikacji i stawia ją z bazą i seedem w tle. Potem cały dzień uruchamiam testy z IDE (panel Testing, debug z breakpointami, `--headed`) — pytest działa na hoście, nie w kontenerze, i trafia w `127.0.0.1:3100` / `:5432` według `BASE_URL` i `DATABASE_URL` z `.env`. Kontenerów nie restartuję między testami; przebudowuję je (`--build`) tylko po zmianie aplikacji, a świeżą bazę dostaję przez `down -v`. Żeby uruchomić te same testy na stagingu, zmieniam `BASE_URL`, a przy fixtures z SQL także `DATABASE_URL`.
- **Dlaczego testy poza kontenerem:** debugowanie i podgląd przeglądarki działają bez konfiguracji. Alternatywa: fixture startująca compose (`pytest-docker`) — jeden klik, ale minuta czekania na każde uruchomienie.
- **Dowód:** `docker-compose.yml`, `.env.example`, sekcja 3 — środowisko testowe.

### Skąd lokalne środowisko bierze kod aplikacji? Czy to „najnowsza wersja”?
- **Odpowiedź:** compose nie pobiera niczego z GitHuba — buduje obraz z **folderu** lokalnego klonu (build context), dokładnie w stanie z tej chwili, łącznie z niezacommitowanymi zmianami. Najnowsza = najnowsza na dysku. Bez `--build` compose użyje starego obrazu. W CI jest inaczej: runner robi czysty checkout konkretnego commita, więc zawsze wiadomo, co jest testowane — dlatego wynik z CI jest wiarygodniejszy niż lokalny.
- **Pułapka:** gdy developer (u mnie agent Grok) jest w połowie pracy, lokalny obraz zawiera niedokończony kod — przy dziwnej porażce najpierw `git status` w klonie aplikacji.
- **Dowód:** sekcja 10 — build context; notatki z Etapu 1.

### Czym jest quality gate i czym różni się od samego CI?
- **Odpowiedź:** CI to automat, który uruchamia testy i pokazuje wynik. Bramką (quality gate) staje się dopiero, gdy wynik **decyduje**, czy kod przejdzie dalej — w GitHubie przez branch protection na `main` z wymaganym zielonym statusem testów. Bez tej reguły czerwony krzyżyk jest tylko ostrzeżeniem i merge można zrobić. Bramkę omija też push bezpośrednio na `main` — dlatego zmiany muszą iść przez PR-y.
- **U mnie:** bramka na PR sklepu (ADR-005); warunek: sklep przechodzi na pracę przez PR-y (otwarta decyzja przed Etapem 5).
- **Dowód:** ADR-005, sekcja 10 — quality gate.

### Jak skonfigurujesz bramkę na PR, gdy testy są w osobnym repo?
- **Odpowiedź:** zapalnikiem jest workflow w **repo aplikacji** (`.github/workflows/tests.yml`, `on: pull_request: branches: [main]`), nie docker-compose — compose to tylko jeden z kroków. Kroki: checkout aplikacji z PR-a → checkout repo testów (prywatne → token jako sekret) → `docker compose up --build --wait` z kodem z PR-a → pytest → upload raportu (`if: always()`) → `down -v`. Na koniec branch protection na `main` wymaga zielonego statusu. Repo testów ma osobny workflow: push/PR (testy na `main` aplikacji) i cron (nightly na STG).
- **Dowód:** sekcja 3 — konfiguracja w GitHubie; ADR-005.

### Dlaczego Dockerfile aplikacji jest w repo aplikacji, a nie w repo testów?
- **Odpowiedź:** Dockerfile to przepis na zbudowanie aplikacji — zmienia się razem z nią (wersja Node, zależności, sposób budowania). W repo aplikacji zmienia się w tym samym commicie co kod, a PR buduje obraz z własnego Dockerfile. W repo testów po cichu by się psuł przy zmianach aplikacji, a naprawiałby go ktoś inny niż autor zmiany. Zasada: repo aplikacji produkuje artefakt (obraz), repo testów go konsumuje (compose). Zespół testów nie commituje do repo aplikacji — przekazuje wymagania z kryteriami akceptacji.
- **Dowód:** ADR-006, `docs/handoff/2026-11-01-etap-1-docker.md`.

### Jak izolujesz dane testowe, gdy staging ma trwałą, współdzieloną bazę?
- **Odpowiedź:** na poziomie **testu**, nie zestawu. Każdy test tworzy własne dane z unikalnym prefiksem (np. własny produkt ze stanem magazynowym) i w teardownie usuwa je po ID. Reset całej bazy przed zestawem odrzuciłem: koliduje z równoległymi przebiegami (nightly + smoke po deployu) i workerami pytest-xdist, niszczy cudze dane, a na produkcji byłby niemożliwy — wolę nawyk, który działa wszędzie. W Dockerze świeża baza na przebieg i tak przychodzi za darmo.
- **Dowód:** ADR-003 (doprecyzowanie 2026-11-01), sekcja 10 — seed.

### Dlaczego GitHub Actions, a nie GitLab CI?
- **Odpowiedź:** CI wybiera się tam, gdzie żyje kod. Repo sklepu jest na GitHubie, deploy na Vercela idzie z GitHuba, a bramka ma blokować PR na GitHubie. Status z GitHub Actions trafia do PR-a i do branch protection od razu. GitLab musiałby kopiować repo (mirror) i odsyłać status przez API, czyli dochodzi jeden element, który może się zepsuć, a nic nie zyskujemy. Na prywatnym repo GitHub daje też więcej darmowych minut (2000 zamiast 400 miesięcznie). GitLab wybrałbym, gdyby firma trzymała kod na GitLabie, zwłaszcza na własnym serwerze; tam mocne są wbudowane rejestry, skanowanie bezpieczeństwa i merge trains. Pojęcia są te same: pipeline, job, runner, service container, cache, artefakty, sekrety, OIDC. Zmienia się składnia YAML, więc przejście z jednego na drugie zajmuje dni, nie tygodnie.
- **Dowód:** ADR-005, sekcja 3 — CI.

### Od czego zacząłbyś budowę frameworka? (Jak zaprojektowałbyś framework od zera?)
- **Odpowiedź:** od pytań, nie od kodu. Pierwszy test piszę dopiero, gdy wiem, co chronię, gdzie testy będą działać i na jakich danych. Kolejność:
  1. **Cel i zakres:** po co framework, kto go używa (QA, deweloperzy, CI), co świadomie zostaje poza nim. Rozmowa z zespołem i przegląd istniejących testów, żeby ich nie dublować.
  2. **Poznanie systemu:** architektura, API (co jest prawdziwym kontraktem), baza, konfiguracja, dane startowe, integracje zewnętrzne do zamockowania.
  3. **Strategia:** ryzyka, piramida (które poziomy i ile scenariuszy na każdym), strategia danych i izolacji, środowiska.
  4. **Decyzje zapisane jako ADR:** język, osobne repo czy wspólne, narzędzia, CI. Z alternatywami i uzasadnieniem, żeby po pół roku było wiadomo, dlaczego tak.
  5. **Powtarzalne środowisko:** aplikacja z bazą i seedem stawiana jedną komendą (Docker). Bez tego testy są niestabilne od pierwszego dnia.
  6. **Szkielet:** struktura, konfiguracja z `.env`, fixtures, linter, markery.
  7. **Jeden test na każdym poziomie, przechodzący przez cały proces** (lokalnie i w CI). Dopiero potem dokładam scenariusze.
  8. **CI jako bramka**, raporty, a potem skalowanie: równoległość, kolejne środowiska, chmura.
- **U mnie:** Etap 0 to punkty 1–4 (cel, referencja API, seed, ADR-001…005). Etap 1 to punkt 5 (sklep w Dockerze, ADR-006/007). Etap 2 to punkt 6. Pełny opis kroków: sekcja 8.
- **Czego unikam (z wcześniejszego frameworka budowanego po omacku):** stanu globalnego przekazywanego między testami, sprzątania „wszystkiego, co utworzył użytkownik X” albo „ostatniego rekordu” zamiast własnych rekordów po ID, haseł w repozytorium, jednego wielkiego `conftest.py`.
- **Co zrobiłbym inaczej:** prosty workflow CI (sam linter) już przy szkielecie, a nie dopiero w Etapie 5. Krótka pętla informacji zwrotnej od pierwszego commita.
- **Dowód:** sekcje 1, 2 i 8; ADR-001…007.

### Dlaczego `pyproject.toml` zamiast `requirements.txt` i `pytest.ini`?
- **Odpowiedź:** jeden plik i zablokowane wersje. `pyproject.toml` to standard Pythona (PEP 621), który czytają pip, uv, Poetry i IDE; trzyma zależności oraz konfigurację pytest i ruff. `requirements.txt` zwykle podaje tylko bezpośrednie zależności, a `uv.lock` blokuje wersje wszystkich pakietów, także zależności zależności, więc lokalnie i w CI instaluje się to samo. Wada: `requirements.txt` jest bardziej znany w starszych projektach, ale `uv export` generuje go jedną komendą.
- **Dowód:** projekt Etapu 2 (D2, D3).

### Dlaczego konfiguracja przez pydantic-settings?
- **Odpowiedź:** walidacja na starcie zamiast błędu w połowie testów. Brak `BASE_URL` albo zły URL daje czytelny komunikat przed pierwszym testem; z `os.getenv` dostaje się `None` i dziwny błąd gdzieś w `requests`. Do tego typy (IDE podpowiada `settings.base_url`), jedno miejsce na wszystkie zmienne, zmienne środowiskowe wygrywają z `.env` (wygodne w CI), a obiekt daje fixture, więc nie ma stanu globalnego. Alternatywa: `python-dotenv` + `os.getenv`, czyli prościej, ale walidację trzeba pisać ręcznie.
- **Dowód:** projekt Etapu 2 (D4).

### Do czego służy pydantic?
- **Odpowiedź:** do walidacji i parsowania danych na podstawie typów Pythona. Kształt danych opisuje się klasą z typami, a pydantic sprawdza dane (zły typ albo brak pola → czytelny błąd), konwertuje je (`"8080"` → `8080`, tekst → `datetime`) i zamienia obiekty na JSON i słowniki. Używany w FastAPI (requesty i odpowiedzi), w konfiguracji aplikacji (pydantic-settings) i przy parsowaniu danych z API. W testach kontraktów mógłby zastąpić jsonschema, ale zostaję przy jsonschema (ADR-002): schemat JSON nie zależy od języka, a dokładność (`additionalProperties: false`) łatwo kontrolować.

### pytest-html czy Allure?
- **Odpowiedź:** pytest-html to jedna wtyczka i jeden plik HTML, czyli prosty artefakt w CI. Allure daje interaktywny raport: kroki, załączniki, historię przebiegów i trendy, ale wymaga osobnego programu (Java) do wygenerowania raportu; w CI może trafiać jako artefakt albo na GitHub Pages z historią. Wybór odkładam do Etapu 5, bo historia przebiegów ma sens dopiero przy regularnych uruchomieniach w CI. Allure częściej pojawia się w ofertach SDET.
- **Dowód:** otwarte decyzje (sekcja 4).

### Dlaczego nie testujesz wszystkiego przez UI? (piramida testów)
- **Odpowiedź:** dla klienta sklep to front, ale gdy „front nie działa”, przyczyna zwykle leży niżej: API zwraca błąd albo w bazie brakuje kolumny, a strona tylko to pokazuje. Test E2E mówi, *że* coś nie działa. Testy API, bazy i kontraktu mówią, *gdzie* i *dlaczego*. Dlatego E2E mam mało, tylko kluczowe ścieżki klienta, a większość scenariuszy sprawdzam niżej, gdzie testy są szybkie i stabilne.
- **Czego unikam:** odwróconej piramidy, czyli setek wolnych testów przez przeglądarkę, które padają z powodów niezwiązanych z błędem (flaky) i nie wskazują przyczyny.
- **Dowód:** sekcja 1 — poziomy testów; Etap 3.

### Skąd wiesz, że dane naprawdę zapisały się w bazie?
- **Odpowiedź:** odpowiedź API mówi tylko, co serwer deklaruje. Dlatego mam osobny poziom testów: akcję wykonuję przez API, a wynik czytam zapytaniem SQL. Po złożeniu zamówienia sprawdzam w tabeli zamówień e-mail, adres, pozycje, sumę, status i termin płatności, a w tabeli produktów stan magazynowy. Sprawdzam też to, czego API nie pokazuje: że odrzucone zamówienie nie zostawiło wiersza ani zmiany stanu, czyli transakcja się wycofała.
- **Dowód:** `tests/db/test_orders_db.py`, `tests/db/test_payments_db.py`; przypadki D-ORD-01…05 w macierzy.

### Jak przygotowujesz dane testowe i jak po sobie sprzątasz?
- **Odpowiedź:** fixture pytest z `yield`. Część przed `yield` wstawia do bazy własny produkt testu z unikalnym identyfikatorem, część po `yield` usuwa go razem z jego zamówieniami i opiniami. Sprzątanie wykona się także wtedy, gdy test padnie. Fixture jest fabryką: test może poprosić o wariant, np. produkt z jedną sztuką na stanie albo z promocją 20%. Usuwam tylko własne rekordy po identyfikatorze, a funkcja sprzątająca odmawia, gdy identyfikator nie ma prefiksu testowego.
- **Czego unikam:** czyszczenia całych tabel i zmieniania danych startowych.
- **Dowód:** ADR-003, ADR-012; `src/jersa/fixtures/products.py`, `src/jersa/db/products.py`.

### Dlaczego test nie zakłada stałych wartości z seeda?
- **Odpowiedź:** dane startowe się zmieniają. Test z liczbą „5 sztuk” na sztywno zrobi się czerwony po zmianie seeda, choć aplikacja działa. Sprawdzam więc różnicę: po zamówieniu 2 sztuk stan ma być o 2 mniejszy niż przed zamówieniem. Z seeda używam tylko rzeczy stałych, jak nazwa produktu, i tylko do odczytu.
- **Dowód:** ADR-013; `tests/db/test_orders_db.py::test_order_reserves_stock`.

### Jak testujesz coś, co zależy od czasu (wygasanie zamówienia)?
- **Odpowiedź:** nie czekam 30 minut i nie zmieniam zegara serwera. Test składa zamówienie, a potem w bazie cofa termin płatności tego jednego, własnego zamówienia. Następnie wywołuje akcję, przy której sklep sprawdza terminy, i czyta wynik: status „anulowane” i przywrócony stan magazynowy. Osobno sprawdzam, że nowe zamówienie dostaje termin dokładnie 30 minut od utworzenia.
- **Alternatywy:** wstrzyknięcie zegara w aplikacji (wymaga zmiany w aplikacji) albo skrócenie limitu zmienną środowiskową.
- **Dowód:** `tests/db/test_payments_db.py::test_expired_order_is_cancelled_and_restocked`, `src/jersa/db/orders.py::backdate_expiry`.

### Co to jest idempotencja i jak ją testujesz?
- **Odpowiedź:** operacja jest idempotentna, gdy powtórzona daje ten sam skutek co wykonana raz. W płatnościach to konieczne, bo operator może wysłać to samo powiadomienie kilka razy. Testuję to wprost: wysyłam powiadomienie o udanej płatności dwa razy i sprawdzam, że drugie jest rozpoznane jako duplikat, a zamówienie dalej jest opłacone raz. Tak samo start płatności: wywołany dwa razy zwraca ten sam adres.
- **Dowód:** `tests/api/test_payments.py` (A-PAY-02, A-PAY-06, A-PAY-10).

### Skąd bierzesz scenariusze testowe?
- **Odpowiedź:** z wymagań, a gdy ich nie ma, najpierw je spisuję. Tu przeczytałem kod i dokumentację API, spisałem reguły biznesowe i dałem je do potwierdzenia właścicielowi sklepu. Dopiero z potwierdzonych reguł powstały przypadki testowe. Kod jest źródłem pytań, nie odpowiedzi: gdy kod robi coś innego, niż mówi reguła, to jest znalezisko. Podejrzenia sprawdzam uruchomieniem, zanim je zgłoszę.
- **Dowód:** ADR-013; `docs/traceability.json` (24 reguły ze źródłem).

### Do czego służy macierz śledzenia wymagań (traceability matrix)?
- **Odpowiedź:** łączy wymaganie, przypadek testowy i test automatyczny. Odpowiada na trzy pytania: czy każda reguła ma test, po co istnieje dany test i które testy ruszyć, gdy reguła się zmienia. U mnie dane są w pliku JSON, PDF generuje skrypt, a test w CI pilnuje, żeby każdy przypadek miał wymaganie i istniejącą funkcję testu. Macierz pokazuje, że test istnieje, a nie, że jest dobry.
- **Kiedy nie warto:** mały zespół bez spisanych wymagań i szybko zmieniający się produkt; wtedy wystarczy identyfikator wymagania w markerze testu albo w raporcie.
- **Dowód:** `docs/traceability-matrix.pdf`, sekcja 7, `tests/framework/test_traceability.py`.

### Do czego służy `parametrize`?
- **Odpowiedź:** do uruchomienia tego samego testu na kilku zestawach danych. Każdy zestaw jest osobnym testem w raporcie, więc od razu widać, który wariant padł. Używam go, gdy logika testu jest ta sama, a zmienia się tylko wejście, np. zamówienie bez każdego z pięciu pól adresu po kolei.
- **Czego unikam:** pętli `for` w teście (pierwsza porażka ukrywa pozostałe) i parametryzacji, w której warianty mają różne asercje.
- **Dowód:** `tests/api/test_orders.py::test_order_without_shipping_field_is_rejected`.

### Dlaczego klient API nie rzuca wyjątku na błąd 400?
- **Odpowiedź:** bo błąd 400 bywa oczekiwanym wynikiem testu. Klient zwraca surową odpowiedź, a status sprawdza test. Gdyby klient rzucał wyjątek, testy negatywne musiałyby go łapać, a z porażki zniknęłaby treść odpowiedzi.
- **Dowód:** `src/jersa/clients/api_client.py`, `src/jersa/clients/commerce.py`.

### Czym jest ruff?
- **Odpowiedź:** linter i formatter Pythona w jednym narzędziu, napisany w Rust, więc sprawdza cały projekt w ułamku sekundy. Linter (`ruff check`) wyłapuje błędy i złe praktyki: nieużywane importy, niezdefiniowane nazwy, zły porządek importów, przestarzałą składnię, typowe pułapki w testach pytest. Formatter (`ruff format`) ujednolica wygląd kodu, jak Black. Zastępuje kilka narzędzi naraz (flake8, isort, pyupgrade, Black), więc jest jedna konfiguracja w `pyproject.toml`.
- **U mnie:** reguły `E`, `F`, `I`, `B`, `UP`, `PT`, długość linii 100. CI uruchamia `ruff check` i `ruff format --check`.
- **Dowód:** `pyproject.toml` (`[tool.ruff]`), `.github/workflows/ci.yml`.

### Co znaczy `uv run pytest -m contract`?
- **Odpowiedź:** `uv run` uruchamia polecenie w środowisku projektu, z pakietami w wersjach z `uv.lock`, bez ręcznej aktywacji `.venv`. `pytest` znajduje i uruchamia testy. `-m contract` (marker) wybiera tylko testy oznaczone etykietą `contract`. Wyrażenia łączy się w cudzysłowie: `-m "smoke and contract"`, `-m "regression and not smoke"`.
- **Marker a katalog:** `-m contract` wybiera po etykiecie, `pytest tests/contract` po położeniu pliku. Marker przydaje się, gdy etykieta przecina katalogi, np. `smoke` mają testy z każdego poziomu.
- **Literówka:** `--strict-markers` w `pyproject.toml` zamienia nieznany marker (np. `-m contrat`) w błąd, zamiast po cichu wybrać 0 testów.
- **Dowód:** `pyproject.toml` (`markers`, `addopts`), `docs/komendy.md`.

### Jakie są sposoby markowania testów w pytest?
- **Odpowiedź:** marker to etykieta przyklejona do testu, po której wybieram zestawy niezależnie od katalogów (smoke po wdrożeniu, regresja w nocy).

  | Sposób | Zasięg |
  |---|---|
  | `pytestmark = [...]` w pliku | wszystkie testy w pliku |
  | `@pytest.mark.smoke` nad funkcją | jeden test |
  | dekorator albo `pytestmark` w klasie | wszystkie testy klasy |
  | `pytest.param(..., marks=...)` w `parametrize` | jeden wariant danych |
  | hook `pytest_collection_modifyitems` w `conftest.py` | według reguły, np. katalogu |
  | `request.applymarker(...)` | dynamicznie, w trakcie testu |

  Markery z różnych poziomów się sumują: test z `pytestmark = regression` w pliku i `@pytest.mark.smoke` nad funkcją ma oba.
- **Moja decyzja:** jawny `pytestmark` w pliku zamiast hooka, bo w małym projekcie wolę widzieć marker obok testu. Wada: trzeba go pamiętać przy nowym pliku. Hook nadawałby go automatycznie, ale byłby niewidoczny dla czytającego.
- **Dowód:** `tests/api/test_cart.py` (`pytestmark` + `@pytest.mark.smoke`), `pyproject.toml`.

### Czym jest hook w pytest i czym różni się od fixture?
- **Odpowiedź:** hook to funkcja o ustalonej nazwie, którą framework sam wywołuje w określonym momencie pracy, a ja ją tylko piszę. Przykłady: `pytest_collection_modifyitems` (po zebraniu testów: dodaj markery, zmień kolejność), `pytest_addoption` (własna opcja linii poleceń), `pytest_runtest_makereport` (po teście: zrzut ekranu przy porażce). Hooki muszą leżeć w `conftest.py` albo w module z `pytest_plugins`; w pliku z testem nie działają.
- **Różnica:** fixture wywołuje się z testu, wymieniając ją w argumentach, a pytest dostarcza wynik. Hook wywołuje narzędzie w swoim momencie i rozpoznaje go po nazwie.
- **Ten sam pomysł:** git hook (skrypt przed commitem), hook w Claude Code (polecenie po akcji agenta).
- **U mnie:** na razie żadnego hooka pytest nie ma. Pierwszy pojawi się prawdopodobnie przy zrzutach i śladach E2E w Etapie 5.

### Gdzie trzymać fixtury: w `conftest.py` czy w osobnych modułach?
- **Odpowiedź:** `conftest.py` to domyślne miejsce, które pytest czyta sam, ale nie jedyne. Fixtury można trzymać w modułach i rejestrować listą `pytest_plugins` w głównym `conftest.py`. Wybrałem moduły, bo jeden wielki `conftest.py` szybko robi się nieczytelny (to błąd z poprzedniego frameworka), fixtury są częścią kodu frameworka w `src/jersa/`, a moduł można zwyczajnie importować.
- **Co zostaje w `conftest.py`:** lista `pytest_plugins` i `base_url`, który nadpisuje fixturę z wtyczki `pytest-base-url`. Testy w `tests/framework/` mają własny `base_url` z adresem zastępczym, bo pytest wybiera najbliższą fixturę.
- **Kiedy `conftest.py` jest lepszy:** fixtura potrzebna tylko testom jednego katalogu (u mnie `tests/e2e/conftest.py` sprząta koszyk przeglądarki).
- **Dowód:** ADR-009, `conftest.py`, `src/jersa/fixtures/`.

### Jak konfiguruje się Playwright w Pythonie i jak przełączyć tryb z oknem (headed)?
- **Odpowiedź:** w Pythonie nie ma odpowiednika `playwright.config.ts`. Konfiguruje się go opcjami pytest (`--browser`, `--headed`, `--slowmo`, `--tracing`, `--video`), `addopts` w `pyproject.toml` oraz fixturami (`browser_context_args` dla rozmiaru okna i języka, `browser_type_launch_args` dla uruchomienia przeglądarki, `base_url`).
- **Podgląd na żywo:** jednorazowo `--headed` w poleceniu. Na stałe lokalnie `HEADED=true` w `.env`. Nie wpisuję `--headed` do `addopts`, bo plik jest wspólny i CI też próbowałoby otworzyć okno. `.env` nie trafia do repo, więc moje ustawienie nie wpływa na CI. Opcja z linii poleceń i zmienna środowiskowa wygrywają z `.env`.
- **Dowód:** `src/jersa/config.py` (`headed`, `is_headed`), `src/jersa/fixtures/browser.py`, `.env.example`.

### Co robi plik `ci.yml` i gdzie uruchamia się CI?
- **Odpowiedź:** `ci.yml` opisuje, co CI robi: zadania i kroki. CI działa na maszynie GitHuba (runner `ubuntu-latest`), nie na moim komputerze, i startuje przy pushu i pull requeście do `main`. U mnie: checkout, instalacja zależności z `uv.lock` (`uv sync --locked`), `ruff check`, `ruff format --check` i `pytest tests/framework`. Bez Dockera, sklepu i `.env`, więc testy sklepu CI jeszcze nie uruchamia (to Etap 5, ADR-005).
- **Dowód:** `.github/workflows/ci.yml`, ADR-011.

### Czym różni się `ci.yml` od reguły ochrony gałęzi i czy CI to już quality gate?
- **Odpowiedź:** to dwie osobne rzeczy. `ci.yml` mówi, **co** CI robi, i wgrywa się go pushem. Reguła ochrony gałęzi (branch protection) decyduje, **czy wynik CI blokuje scalenie**, i żyje w ustawieniach repo na GitHubie (Settings → Branches), nie w pliku w repo. Push żadnej reguły nie przenosi: ustawia się ją osobno ręcznie albo przez `gh api`. Z `ci.yml` bierze się tylko nazwa zadania, którą reguła ma wymagać (u mnie `lint-and-framework-tests`).
- **Czy to bramka:** samo CI nie. Bez reguły czerwony wynik jest ostrzeżeniem, a push wprost na `main` go omija. Bramką staje się, gdy zmiany idą przez pull request, a reguła wymaga zielonego statusu przed scaleniem. Reguła działa na pull requesty, nie na push. Żeby obowiązywała także właściciela repo, trzeba wyłączyć jej obchodzenie przez administratora.
- **Kolejność włączania:** najpierw jednorazowy push i zielony pierwszy przebieg (żeby nazwa statusu była znana i CI sprawdzone na czystej maszynie), potem reguła. Włączona przed pierwszym przebiegiem mogłaby zablokować własną naprawę.
- **Zakres:** bramka na framework sprawdza kod frameworka. Bramka na sklep (testy na kodzie z PR-a aplikacji) to Etap 5.
- **U mnie dziś:** reguły nie ma. GitHub zwraca „Branch not protected”.
- **Dowód:** ADR-005, powiązane pytanie „Czym jest quality gate i czym różni się od samego CI?”, słownik: „Quality gate i branch protection”.

### Jak uruchamiasz testy równolegle i co musi być prawdą, żeby to działało?
- **Odpowiedź:** `pytest-xdist` (`-n 4`) startuje 4 procesy robocze i rozdziela między nie testy. Działa, gdy testy są niezależne: żaden nie zakłada kolejności ani cudzych danych. U mnie każdy test, który coś zmienia, dostaje własny produkt (`test-<hex>`) i własną sesję koszyka, a po teście usuwa tylko własne rekordy po ID. Asercje porównują stan z tym sprzed akcji, nie z liczbami z seeda.
- **Dowód:** trzy przebiegi z rzędu na 4 procesach: 150 passed, w bazie zero śladów, seed bez zmian (suma kontrolna). ADR-012, ADR-013, ADR-015.

### Co dzieje się z fixturą `scope="session"` przy xdist i co z testem, który pada tylko równolegle?
- **Odpowiedź:** każdy proces roboczy ma własną kopię fixtur sesyjnych (własna konfiguracja, własne połączenie z bazą, własna przeglądarka), więc nic nie jest współdzielone między procesami. Współdzielone jest tylko to, co poza procesami: baza i sklep. Test, który pada tylko równolegle, ma ukrytą zależność, np. czyta globalne dane albo liczy na kolejność. Naprawiam przyczynę (własne dane testu), a `serial` albo `loadfile` biorę dopiero, gdy test z natury dotyka stanu globalnego, i opisuję wyjątek.
- **Dowód:** `src/jersa/fixtures/` (fixtury sesyjne: `settings`, `db`, `schema_registry`, `browser_type_launch_args`), ADR-015.

### Czy równoległość zawsze przyspiesza testy?
- **Odpowiedź:** nie. Każdy proces ma stały koszt startu (import, zebranie testów, w E2E własna przeglądarka), więc dla krótkich testów start przewyższa zysk. U mnie zestaw 150 testów trwał ok. 15 s zarówno na jednym, jak i na czterech procesach, E2E było wolniejsze (6,3 → 8,0 s), a 67 szybkich testów frameworka ok. 8–9 razy wolniejsze (0,5 → 4,8 s), więc w CI idą z `-n 0`. Ograniczeniem bywa też sama aplikacja pod obciążeniem; u mnie tego nie mierzyłem. Dlatego mierzę przed i po.
- **Dowód:** sekcja 6 („Testy równolegle nie są szybsze”), ADR-015, `ci.yml`.

### Jak zbudowałeś bramkę jakości, gdy sklep i testy są w dwóch repozytoriach?
- **Odpowiedź:** workflow leży w repo sklepu, bo to tam powstaje zmiana. Na każdy pull request do `main` buduje sklep z kodu PR-a w Dockerze, pobiera repo testów i uruchamia cały zestaw (kontrakt, API, baza, E2E). Wynik wraca do PR-a jako status `tests`. Repo testów jest publiczne, więc checkout nie wymaga tokena. Jeśli zmiana w sklepie świadomie zmienia zachowanie, robię gałąź o tej samej nazwie w repo testów, a workflow ją wybierze; bez niej bierze `main`.
- **Czego unikam:** `repository_dispatch` (wynik nie wraca do PR-a), ręcznego wskazywania gałęzi testów i ponawiania samych testów (ukrywa prawdziwe porażki).
- **Dowód:** ADR-016, `tests.yml` w repo sklepu, PR #1 i kontrola czerwieni w PR #2 (zamknięty).

### Skąd wiesz, że bramka naprawdę wykrywa błąd, a nie tylko wygląda na zieloną?
- **Odpowiedź:** zielony przebieg niczego nie dowodzi, bo workflow z błędem w konfiguracji też byłby zielony. Dlatego robię kontrolę czerwieni: tymczasowy PR z celowo złamaną regułą (zaokrąglanie ceny) i sprawdzam, że status jest czerwony, test wskazuje regułę (`assert 22 == 23`) i są logi do diagnozy. Dla samej blokady Merge to osobne sprawdzenie reguły ochrony gałęzi.
- **Uczciwie:** w prywatnym repo na darmowym planie GitHub reguł ochrony nie egzekwuje, więc moja bramka na sklepie jest informacyjna. Egzekwowanie dołożę przez płatny plan albo przez bramkę na wdrożeniu.
- **Dowód:** sekcja 6 („Reguła ochrony zapisana, ale nieegzekwowana”), ADR-016.

### Czym różni się `pull_request` od `pull_request_target` i jak zabezpieczasz workflow przed złośliwą nazwą gałęzi?
- **Odpowiedź:** `pull_request` uruchamia workflow z kodu PR-a; dla PR-ów z forków dostaje on tylko token do odczytu i bez sekretów, a dla gałęzi z tego samego repo ma dostęp do sekretów, jeśli workflow je wskazuje. `pull_request_target` uruchamia workflow z gałęzi docelowej z sekretami i zapisem, więc nie wolno w nim wykonywać kodu z PR-a. Używam `pull_request`, bez sekretów i z `permissions: contents: read`. Nazwa gałęzi to dane od użytkownika: wstawiona do skryptu przez `${{ github.head_ref }}` mogłaby wykonać polecenie. Przekazuję ją przez zmienną środowiskową i cytuję w skrypcie. `actionlint` wykrywa takie wstawienie, co sprawdziłem na celowo zepsutej kopii.
- **Dowód:** `tests.yml` (krok „Wybór gałęzi testów”), ADR-016.

### Co robisz, gdy bramka bywa czerwona bez powodu (flaky)?
- **Odpowiedź:** najpierw rozróżniam awarię infrastruktury od porażki testu. Chwilowy błąd sieci przy budowie obrazu (`npm ci ... ECONNRESET`) ponawiam do trzech razy, bo nie dotyczy zmiany. Samych testów nie ponawiam, bo ukryłbym prawdziwy błąd. Przy porażce testu zostają ślady Playwrighta i logi kontenerów jako artefakty, więc przyczynę ustalam z dowodu, a nie z zgadywania. Nie naprawiam „na zapas”: jednorazowej porażki E2E, której nie dało się odtworzyć, nie poprawiałem, tylko zapisałem i zostawiłem artefakty na następny raz.
- **Dowód:** sekcja 6 („Bramka czerwona przez chwilowy błąd sieci”) i opis Etapu 5A w sekcji 2 (jednorazowa porażka E2E w symulacji CI).

---

## 10. Słownik pojęć

<!-- **Pojęcie:** definicja własnymi słowami -->

### SUT (System Under Test)
- **Definicja:** system, który testujemy — w odróżnieniu od narzędzi, którymi testujemy.
- **U mnie:** SUT = sklep jersa-storefront (Next.js + API BFF + Postgres). Framework (pytest, Playwright, requests) to **nie** SUT — to narzędzie testujące.
- **Dlaczego to rozróżnienie jest ważne:** pozwala jasno wyznaczyć granice: co kontrolujemy i stawiamy na potrzeby testów (SUT w Dockerze), a co jest zależnością zewnętrzną, którą mockujemy (PayU). Pomaga też w diagnozie porażki: błąd w SUT czy błąd w teście/frameworku?
- **Pokrewne:** *DUT* (Device Under Test) w testach sprzętu; *AUT* (Application Under Test) — często używany zamiennie.

### Seed (dane startowe)
- **Definicja:** skrypt lub plik, który wypełnia pustą bazę znanym, przewidywalnym zestawem danych startowych.
- **U mnie:** `fixtures/catalog.json` + `scripts/seed-catalog.ts` w sklepie → 5 produktów, 5 szt. na każdy rozmiar, 2 opinie CASTELLO. Uruchamiany przez `prepare-database.mjs` w usłudze `db-init`.
- **Dlaczego jest ważny:** testy potrzebują punktu wyjścia, który zawsze wygląda tak samo. Dzięki seedowi wiadomo, że CASTELLO kosztuje 350 zł i ma rozmiar 36 — test może na tym polegać bez tworzenia produktu.
- **Seed vs dane tworzone przez test:**

  | | Seed | Dane testu |
  |---|---|---|
  | Kto tworzy | skrypt przy starcie środowiska | sam test (fixture) |
  | Kiedy | raz, przed wszystkimi testami | w trakcie testu |
  | Co zawiera | dane referencyjne (katalog) | dane scenariusza (koszyk, zamówienie, opinia) |
  | Sprzątanie | nie — reset całego środowiska | tak — teardown usuwa własne rekordy |

- **Pułapka (seed):** testy nie powinny **zmieniać** danych seedu w sposób trwały (np. wyczerpać stanu magazynowego) — inaczej kolejny przebieg startuje z innego punktu. Patrz: otwarta decyzja o stanie magazynowym (sekcja 4).

### Docker — podstawowe pojęcia
- **Definicja:** narzędzie, które pakuje aplikację razem z jej środowiskiem (runtime, biblioteki, konfiguracja), żeby działała identycznie na każdej maszynie. Analogia: kontener transportowy — port nie musi wiedzieć, co jest w środku.
- **Pojęcia:**

  | Pojęcie | Co to jest | U mnie |
  |---|---|---|
  | Dockerfile | przepis na zbudowanie obrazu | jak zbudować sklep Next.js |
  | Obraz (image) | zbudowany, niezmienny pakiet | obraz sklepu |
  | Kontener | uruchomiony obraz (odizolowany proces) | działający sklep na porcie 3000 |
  | docker-compose | opis kilku kontenerów działających razem | sklep + Postgres + sieć między nimi |
  | Wystawienie portu | `host:kontener` — udostępnia port kontenera na hoście | `127.0.0.1:3100:3000`, `127.0.0.1:5432:5432` |
  | Volume | dane, które przeżywają restart kontenera | w testach celowo usuwane (`down -v`) |

- **Kontener ≠ maszyna wirtualna:** dzieli jądro systemu z hostem, więc startuje w sekundy i zużywa mało zasobów.

### Ephemeral environment (środowisko tymczasowe)
- **Definicja:** środowisko stawiane na jeden przebieg / jeden PR i niszczone po nim.
- **U mnie:** `docker compose up` → testy → `docker compose down -v`, lokalnie i w CI. Vercel preview deployments to też środowiska tymczasowe.
- **Dlaczego ważne:** brak kolejki do wspólnego środowiska, zawsze czysty stan, testy na każdy push.

### Shift-left
- **Definicja:** przesuwanie testów jak najwcześniej w procesie wytwarzania (w lewo na osi czasu: kod → PR → INT → STG → PROD).
- **Dlaczego:** im wcześniej błąd zostanie wykryty, tym taniej go naprawić.
- **Oś (od lewej):** review wymagań → testy jednostkowe → testy lokalnie przed pushem → bramka na PR → staging → produkcja.
- **U mnie:** bramka na PR sklepu (ADR-005) — testy zmian sklepu przed merge zamiast dopiero po deployu. To przesunięcie w lewo, **nie pełny shift-left**: wcześniej są jeszcze testy jednostkowe sklepu (Vitest) i testy uruchamiane lokalnie w Dockerze przed pushem.

### Quality gate (bramka jakości) i branch protection
- **Definicja:** punkt w procesie, przez który kod nie przejdzie dalej bez spełnienia warunku (np. zielonych testów). Analogia: kontrola bezpieczeństwa na lotnisku.
- **Branch protection:** reguła GitHuba na gałęzi (Settings → Branches), np. „merge do `main` wymaga zielonego statusu `tests`” — to ona zamienia CI z informacji w bramkę.
- **U mnie:** bramka na PR sklepu (ADR-005), dopiero od Etapu 5 i po przejściu sklepu na PR-y.

### Workflow, trigger, runner (GitHub Actions)
- **Workflow:** plik YAML w `.github/workflows/` — opis *kiedy* i *co* uruchomić.
- **Trigger (`on:`):** zdarzenie, które uruchamia workflow — `pull_request`, `push`, `schedule` (cron, UTC), `workflow_dispatch` (ręcznie).
- **Runner:** maszyna wirtualna GitHuba (np. `ubuntu-latest`) stawiana na jeden przebieg i kasowana po nim. Darmowy limit dla prywatnych repo ok. 2000 min/mies.
- **Gdzie widać wynik:** zakładka Actions (logi, artefakty) i status przy PR/commicie.

### Build context (kontekst budowania)
- **Definicja:** folder, który Docker dostaje do zbudowania obrazu — Dockerfile widzi tylko pliki z tego folderu (minus `.dockerignore`).
- **U mnie:** `STOREFRONT_PATH` → lokalny klon sklepu; w CI → katalog checkoutu z PR-a. Obraz = stan folderu w chwili `--build`, nie stan GitHuba.

---

## 11. Źródła

<!-- tytuł / link → co z tego wyniosłem -->
