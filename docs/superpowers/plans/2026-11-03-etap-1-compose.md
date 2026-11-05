# Etap 1 — compose w repo testów: plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** jedną komendą (`docker compose up -d --build --wait`) postawić sklep jersa-storefront z Postgresem i seedem na `localhost:3000` / `localhost:5432`.

**Architecture:** `docker-compose.yml` w repo testów buduje obraz z Dockerfile w lokalnym klonie sklepu (commit `4c1a64d`). Trzy usługi: `postgres` → `db-init` (etap `builder`, `prepare-database.mjs`, kończy się) → `app` (etap `runner`, `node server.js`). Framework testowy działa na hoście.

**Tech Stack:** Docker Compose v2 (2.23+), `postgres:16`, obraz sklepu Node 22 bookworm-slim.

**Spec:** `docs/superpowers/specs/2026-11-01-etap-1-docker-design.md`

## Global Constraints

- Postgres: użytkownik / hasło / baza `jersa` / `jersa` / `jersa`, port `5432:5432`.
- Sklep: port `3000:3000`, `COMMERCE=own`, `DATABASE_URL=postgresql://jersa:jersa@postgres:5432/jersa` (wewnątrz sieci compose).
- Z hosta (testy): `BASE_URL=http://localhost:3000`, `DATABASE_URL=postgresql://jersa:jersa@localhost:5432/jersa`.
- Kontekst builda: `STOREFRONT_PATH`, domyślnie `../../Documents/Repos/jersa-storefront`.
- `ADMIN_PASSWORD` domyślnie `dev-admin`.
- Healthcheck aplikacji przez `node -e fetch(...)` (obraz bez `curl`), sukces = odpowiedź search zawiera `zakiet-castello`.
- `.env` nie trafia do gita; wzór w `.env.example`.
- Repo sklepu tylko do odczytu.

## Review Focus

1. Port `5432` lub `3000` zajęty na hoście (lokalny Postgres, `next dev` sklepu) → `up` kończy się czytelnym błędem portu, nie cichym „unhealthy”. Weryfikacja: Task 1 Step 3 — przy błędzie sprawdzić `netstat -ano | findstr ":3000 :5432"`.
2. Drugi `up` bez `-v` (baza już istnieje) → `db-init` przechodzi ponownie (seed tylko dopisuje brakujące), sklep wstaje. Task 2 Step 4.
3. Zła ścieżka `STOREFRONT_PATH` → błąd „build context” przy `up`, nie stary obraz. Task 1 Step 3 (wypisać `docker compose config` i sprawdzić ścieżkę `context`).
4. `db-init` się wywala → `app` nie startuje; diagnoza `docker compose logs db-init`. Opisane w KNOWLEDGE sekcja 6, jeśli wystąpi.
5. Daemon Dockera nie działa → `docker info` przed `up`. Task 1 Step 1.

---

### Task 1: `docker-compose.yml` i `.env.example` — sklep wstaje

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create (lokalnie, gitignore): `.env` — kopia `.env.example`

**Interfaces:**
- Produces: usługi `postgres`, `db-init`, `app`; obrazy `jersa-storefront:builder`, `jersa-storefront:runner`; wolumen `pgdata`; zmienne `.env`: `STOREFRONT_PATH`, `ADMIN_PASSWORD`, `BASE_URL`, `DATABASE_URL` (Etap 2 czyta `BASE_URL` i `DATABASE_URL`).

- [ ] **Step 1: Sprawdź Dockera**

Run: `docker info --format "{{.ServerVersion}}"` oraz `docker compose version`
Expected: wersja serwera (bez błędu połączenia) i Compose ≥ 2.23.

- [ ] **Step 2: Napisz `docker-compose.yml` i `.env.example`, skopiuj do `.env`**

- `name: jersa`.
- `postgres`: `postgres:16`, `POSTGRES_USER/PASSWORD/DB=jersa`, wolumen `pgdata:/var/lib/postgresql/data`, healthcheck `pg_isready -U jersa -d jersa` (interval 2s, retries 30).
- `db-init`: `build: {context: ${STOREFRONT_PATH:-../../Documents/Repos/jersa-storefront}, target: builder}`, `image: jersa-storefront:builder`, `command: ["node", "scripts/prepare-database.mjs"]`, `depends_on: postgres: service_healthy`, `restart: "no"`.
- `app`: ten sam context, `target: runner`, `image: jersa-storefront:runner`, `depends_on: db-init: service_completed_successfully`, healthcheck (interval 5s, start_period 20s, retries 30):
  `node -e "fetch('http://localhost:3000/api/commerce/search?q=castello').then(r=>r.text()).then(t=>process.exit(t.includes('zakiet-castello')?0:1)).catch(()=>process.exit(1))"`
- `.env.example`: cztery zmienne z Interfaces z komentarzem po polsku, że `DATABASE_URL` to widok z hosta (`localhost`), a kontenery używają `postgres`.

- [ ] **Step 3: Uruchom**

Run: `docker compose config` (sprawdź ścieżkę `context`), potem `docker compose up -d --build --wait`
Expected: `postgres` healthy, `db-init` exited (0), `app` healthy; komenda kończy się kodem 0.

- [ ] **Step 4: Sprawdź search z hosta**

Run: `curl -s "http://localhost:3000/api/commerce/search?q=castello"`
Expected: JSON `{"products":[...]}` z `"slug":"zakiet-castello"`.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "Etap 1: docker-compose (postgres, db-init, app) i .env.example"
```

### Task 2: kryteria akceptacji i dokumentacja

**Files:**
- Modify: `KNOWLEDGE.md` (sekcja 2 — notatki Etapu 1 i checkbox; sekcja 6 — problemy, jeśli wystąpiły; sekcja 8 — krok 17)
- Modify: `CLAUDE.md` (status projektu; struktura — `docker-compose.yml`)
- Modify: `docs/superpowers/specs/2026-11-01-etap-1-docker-design.md` (status)

**Interfaces:**
- Consumes: działające usługi z Task 1.

- [ ] **Step 1: PDP ze zdjęciami i statyką**

Run: `curl -s -o NUL -w "%{http_code}" http://localhost:3000/produkt/zakiet-castello`, `curl -s -o NUL -w "%{http_code}" http://localhost:3000/preview/outfits/3.jpg`, oraz pobierz jeden adres `/_next/static/...` z HTML PDP.
Expected: `200` dla wszystkich trzech; HTML PDP zawiera `CASTELLO` i cenę `350`.

- [ ] **Step 2: Baza z hosta**

Run: `docker compose exec postgres psql -U jersa -d jersa -c "SELECT slug, \"stockBySize\" FROM \"ProductRow\" ORDER BY slug;"`
Expected: 5 slugów z `docs/api-reference.md`; w `stockBySize` wartości `5`. Inna liczba → zapisać w notatkach Etapu 1 (seed się zmienił).

- [ ] **Step 3: Świeża baza po `down -v`**

Run: `docker compose exec postgres psql -U jersa -d jersa -c "UPDATE \"ProductRow\" SET \"stockBySize\"='{}' WHERE slug='zakiet-castello';"`, potem `docker compose down -v` i `docker compose up -d --wait`, potem zapytanie ze Step 2.
Expected: CASTELLO znów ma stan `5` na rozmiar.

- [ ] **Step 4: Drugi `up` bez `-v`**

Run: `docker compose down` (bez `-v`), `docker compose up -d --wait`
Expected: kod 0, `db-init` exited (0), search zwraca CASTELLO.

- [ ] **Step 5: Zapisz wynik w dokumentach i commit**

KNOWLEDGE sekcja 2: wyniki kryteriów, czasy pierwszego i kolejnego builda, znana różnica (blog prerenderowany z MockCommerce, odświeżenie po 60 s); checkbox Etapu 1 po pushu sklepu i zielonym deployu Vercela (do potwierdzenia przez człowieka). Sekcja 8 — krok 17: „Postaw środowisko jedną komendą i sprawdź je kryteriami akceptacji”. CLAUDE.md: status.

```bash
git add KNOWLEDGE.md CLAUDE.md docs/superpowers/specs/2026-11-01-etap-1-docker-design.md
git commit -m "Etap 1: wynik kryteriów akceptacji środowiska DEV"
```
