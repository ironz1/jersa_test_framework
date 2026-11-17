# Etap 5A — Bramka testów na PR sklepu: Implementation Plan

> **Wynik wykonania (2026-11-17):** zadania 1, 2 i 4 wykonane zgodnie z planem (z dodanym ponawianiem budowy). W zadaniu 3 kontrola czerwieni wykonana po scaleniu PR-a z workflow (inaczej niż w planie, bo workflow musi być na `main`, żeby PR się uruchomił); kroki 4–5 (reguła ochrony i sprawdzenie blokady) **nie dały się wykonać**: reguła nie jest egzekwowana w prywatnym repo na darmowym planie. Szczegóły: ADR-016 w `KNOWLEDGE.md`. Checkboxy poniżej nie były odhaczane; stan prac to ledger i historia gita.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** workflow w repo sklepu uruchamia cały zestaw testów na każdym PR-ze do `main` i zgłasza status `tests`, który właściciel wskaże w regule ochrony.

**Architecture:** `tests.yml` w repo sklepu: checkout PR-a, checkout publicznego repo testów (gałąź o tej samej nazwie, inaczej `main`), `docker compose up --build` z `STOREFRONT_PATH` na sklep z PR-a, `pytest`, artefakty i sprzątanie. Pliki sklepu zmieniamy tylko na gałęzi `ci-bramka-testow`, bez pushu bez zgody właściciela. Dokumentacja w repo testów.

**Tech Stack:** GitHub Actions, Docker Compose, uv, pytest, Playwright, `actionlint` (przez `uvx actionlint-py`), `gh`.

**Spec:** `docs/superpowers/specs/2026-11-17-etap-5a-bramka-sklepu-design.md`

## Global Constraints

- Repo sklepu: lokalny klon repo sklepu (zdalne: `ironz1/jersa-storefront`, prywatne). Zmiany tylko w `.github/workflows/tests.yml` i `AGENTS.md`; kod sklepu nietknięty.
- Zadanie (job) nazywa się **`tests`**: to nazwa statusu w regule ochrony.
- Bez sekretów; `permissions: contents: read`; `github.head_ref` tylko przez `env:`, nigdy w `run:` przez `${{ }}`; bez `pull_request_target`.
- Akcje przypięte do pełnych wersji; wersję sprawdzać przez `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`. Znane: `actions/checkout@v7`, `astral-sh/setup-uv@v10.3.3`.
- `timeout-minutes: 20`; `concurrency` po nazwie gałęzi z `cancel-in-progress: true`.
- **Push do repo sklepu, otwarcie PR-a i ustawienie reguły ochrony tylko po zgodzie właściciela** (w repo sklepu push na `main` deployuje na Vercel; `AGENTS.md` zabrania pushu bez prośby). Pliki lokalne repo testów, wykluczone z gita, nie trafiają do commitów.
- Repo testów: gałąź `etap-5a-bramka-sklepu`; bramka wymaga PR-a; push i merge po zgodzie.

## Review Focus

1. Nazwa gałęzi ze znakami specjalnymi (`feat/x y`, `$(...)`, backtick): nie może wykonać polecenia ani zepsuć wyboru gałęzi testów.
2. Brak gałęzi o tej samej nazwie w repo testów: bramka używa `main`, nie pada na `git ls-remote`.
3. Sprzątanie po przebiegu (`down -v` z `if: always()`) także po anulowaniu przez `concurrency`.
4. Porażka testów: artefakty ze śladami i logi kontenerów są dostępne, a status jest czerwony (nie „pominięty”).
5. Runner z 2 vCPU: 4 procesy z Chromium nie mogą dawać losowych porażek (czasy odpowiedzi); jeśli dają, `-n 2` tylko w CI.

---

### Task 1: Workflow `tests.yml` (sprawdzony lokalnie)

**Files:**
- Create: `.github/workflows/tests.yml` w lokalnym klonie repo sklepu
- Modify (commit tylko tego pliku z zastrzeżeniem): `AGENTS.md` (już zmieniony, niezacommitowany)

**Interfaces:**
- Produces: job `tests` w workflow o nazwie `tests`; kroki z `id: tests-ref` (wyjście `ref`); artefakty `traces-${{ github.run_id }}` i `docker-logs-${{ github.run_id }}`.

- [ ] **Step 1: Gałąź w repo sklepu.** `git switch -c ci-bramka-testow` (z `main`; niezwiązane zmiany robocze zostają niezacommitowane). Expected: `Switched to a new branch`.
- [ ] **Step 2: Sprawdź wersje akcji:** `gh api repos/actions/upload-artifact/releases/latest --jq .tag_name`, potem `gh api repos/actions/upload-artifact/git/ref/tags/<tag>` dla pełnej wersji (np. `v4.6.2`). Wpisz do pliku wersję pełną. Expected: odpowiedź JSON z `object.sha`.
- [ ] **Step 3: Napisz test lokalny (czerwony): `uvx actionlint-py .github/workflows/tests.yml` przed utworzeniem pliku.** Expected: błąd „no such file”/brak plików (punkt odniesienia).
- [ ] **Step 4: Utwórz `tests.yml` o strukturze:**

```yaml
name: tests
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
concurrency:
  group: tests-${{ github.head_ref }}
  cancel-in-progress: true
jobs:
  tests:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v7
        with: { path: shop }
      - name: Wybór gałęzi testów (ta sama nazwa albo main)
        id: tests-ref
        env:
          HEAD_REF: ${{ github.head_ref }}
        run: |
          if git ls-remote --exit-code --heads https://github.com/ironz1/jersa_test_framework.git "refs/heads/${HEAD_REF}" >/dev/null 2>&1; then
            echo "ref=${HEAD_REF}" >> "$GITHUB_OUTPUT"
          else
            echo "ref=main" >> "$GITHUB_OUTPUT"
          fi
      - uses: actions/checkout@v7
        with:
          repository: ironz1/jersa_test_framework
          ref: ${{ steps.tests-ref.outputs.ref }}
          path: tests
      - uses: astral-sh/setup-uv@v10.3.3
      - name: Zależności testów
        working-directory: tests
        run: uv sync --locked
      - name: Przeglądarka
        working-directory: tests
        run: uv run playwright install --with-deps chromium
      - name: Sklep w Dockerze
        working-directory: tests
        env:
          STOREFRONT_PATH: ${{ github.workspace }}/shop
        run: docker compose up -d --build --wait
      - name: Testy
        working-directory: tests
        env:
          BASE_URL: http://127.0.0.1:3100
          DATABASE_URL: postgresql://jersa:jersa@127.0.0.1:5432/jersa
        run: uv run pytest --tracing retain-on-failure
      - name: Artefakty (ślady)
        if: always()
        uses: actions/upload-artifact@<pełna wersja z kroku 2>
        with:
          name: traces-${{ github.run_id }}
          path: tests/test-results
          if-no-files-found: ignore
      - name: Logi kontenerów
        if: failure()
        working-directory: tests
        env:
          STOREFRONT_PATH: ${{ github.workspace }}/shop
        run: docker compose logs --no-color > ../docker-logs.txt
      - name: Artefakty (logi)
        if: failure()
        uses: actions/upload-artifact@<pełna wersja z kroku 2>
        with:
          name: docker-logs-${{ github.run_id }}
          path: docker-logs.txt
      - name: Sprzątanie
        if: always()
        working-directory: tests
        env:
          STOREFRONT_PATH: ${{ github.workspace }}/shop
        run: docker compose down -v
```

  Odpowiada to spec; wykonawca poprawia składnię według wyniku `actionlint`, nie zmieniając decyzji ze spec (nazwa joba, brak sekretów, `head_ref` tylko w `env`).
- [ ] **Step 5: `uvx actionlint-py .github/workflows/tests.yml`.** Expected: brak błędów (kod wyjścia 0). Każdy ostrzegawczy komunikat o wstrzyknięciu (`script injection`) traktuj jako błąd.
- [ ] **Step 6: Test wyboru gałęzi (Review Focus 1 i 2):** w bashu uruchom ten sam kod `if git ls-remote …` z `HEAD_REF` równym kolejno: `main` (istnieje), `nie-istnieje-xyz` (brak), `x y` i `$(touch /tmp/pwn)` (znaki specjalne). Expected: dla `main` wynik `ref=main`; dla pozostałych `ref=main`; plik `/tmp/pwn` nie powstaje; żadnego błędu.
- [ ] **Step 7: Symulacja CI lokalnie (czyste środowisko).** `git clone https://github.com/ironz1/jersa_test_framework.git` do katalogu w scratchpadzie (bez `.env`); `docker compose down -v` w bieżącym repo testów; w klonie: `uv sync --locked`, `uv run playwright install chromium`, `STOREFRONT_PATH=<ścieżka sklepu> docker compose up -d --build --wait`, potem `BASE_URL=… DATABASE_URL=… uv run pytest --tracing retain-on-failure`. Expected: 150 passed i brak plików `.env` w klonie. Na koniec `docker compose down -v` w klonie i ponowne uruchomienie głównej wersji środowiska.
- [ ] **Step 8: Commit w repo sklepu (tylko dwa pliki):** `git add .github/workflows/tests.yml AGENTS.md`, `git commit -m "CI: bramka testów na PR i zasady pracy przez pull requesty"`. Nie pushuj. Expected: `git status` pokazuje tylko niezwiązane zmiany robocze.

### Task 2: Pierwszy przebieg na PR-ze (wymaga zgody właściciela)

**Files:** brak nowych; ewentualne poprawki `tests.yml`.

**Interfaces:** Consumes: gałąź `ci-bramka-testow` z Task 1.

- [ ] **Step 1: Zapytaj właściciela o zgodę** na `git push -u origin ci-bramka-testow` w repo sklepu i otwarcie PR-a do `main` (to jedyny krok z efektem na zewnątrz; push na gałąź nie deployuje na Vercel). Bez zgody zatrzymaj się tutaj i zgłoś.
- [ ] **Step 2: Po zgodzie:** push i `gh pr create --base main --title "CI: bramka testów na PR" --body …` (z linią o Claude Code na końcu). Expected: URL PR-a; workflow `tests` startuje.
- [ ] **Step 3: Obserwuj przebieg** (`gh run watch` lub `gh run view --log-failed`). Zapisz czas każdego kroku (`gh run view --json jobs`). Expected: zielony status `tests`.
- [ ] **Step 4: Przy porażce:** napraw przyczynę w `tests.yml` (jedna poprawka na push, komunikat z przyczyną), push, powtórz. Przy losowych porażkach pod obciążeniem (Review Focus 5) dodaj `-n 2` do kroku „Testy” tylko w CI i zapisz powód w komentarzu YAML. Expected: dwa kolejne zielone przebiegi.
- [ ] **Step 5: Sprawdź artefakty i sprzątanie:** przebieg zielony zawiera artefakt `traces-<id>` (może pusty, `if-no-files-found: ignore`); krok „Sprzątanie” wykonany.

### Task 3: Kontrola czerwieni i reguła ochrony

**Files:** brak (gałąź tymczasowa w repo sklepu; zmiany po stronie GitHuba wykonuje właściciel).

**Interfaces:** Consumes: zielony przebieg z Task 2 (nazwa statusu `tests` widoczna w Settings).

- [ ] **Step 1: Zapytaj właściciela o zgodę** na tymczasowy PR z celowo zmienioną ceną lub nazwą produktu w kodzie sklepu (kontrola czerwieni) i jego zamknięcie bez scalania.
- [ ] **Step 2: Po zgodzie:** gałąź `ci-test-czerwien` z jedną zmianą w sklepie, która łamie regułę (np. inna cena w `fixtures`/seedzie; wykonawca wybiera po przeczytaniu kodu), push, PR. Expected: status `tests` **czerwony**, artefakty `traces-*` i `docker-logs-*` dostępne, komunikat porażki wskazuje test i różnicę.
- [ ] **Step 3: Zamknij PR bez scalania i usuń gałąź zdalną** (`gh pr close --delete-branch`). Expected: `main` bez zmian.
- [ ] **Step 4: Poproś właściciela o ustawienie reguły** w Settings → Branches repo sklepu: wymagany PR, wymagany status `tests`, bez obejścia przez administratora, blokada force push. Wypisz mu te opcje.
- [ ] **Step 5: Weryfikacja reguły:** właściciel potwierdza (zrzut lub opis), że przy czerwonym PR-ze Merge jest zablokowany, a `git push origin main` jest odrzucone. Scalenie PR-a `ci-bramka-testow` robi właściciel po zielonym statusie.

### Task 4: Dokumentacja w repo testów

**Files:**
- Modify: `KNOWLEDGE.md` (sekcje 2, 3, 4, 6 jeśli były problemy, 8, 9), `CLAUDE.md` (status, struktura: bramka żyje w repo sklepu), `docs/komendy.md` (sekcja o CI)

**Interfaces:** Consumes: wyniki z Task 1–3 (czasy kroków, liczba poprawek, ewentualne `-n 2`).

- [ ] **Step 1: `KNOWLEDGE.md`:** sekcja 2 — wpis „Etap 5A” z wynikami i czasem przebiegu, checkbox Etapu 5 zostaje otwarty (zostaje 5B); sekcja 3, „CI — konfiguracja w GitHubie”: popraw punkty 1–2 (repo testów jest publiczne, token niepotrzebny; wskazówka na 5B: tam token do prywatnego sklepu będzie potrzebny); tabela otwartych decyzji: zamknij wiersze „mechanizm bramki” i „praca przez PR-y”.
- [ ] **Step 2: ADR-016** z polem „Na rozmowie” (1–3 proste zdania): checkout publicznych testów bez tokena, gałąź o tej samej nazwie, obraz bez cache, `head_ref` przez `env`. Sekcja 6 — każdy problem napotkany w Task 2 (jeśli były). Sekcja 8 — kroki 35–36. Sekcja 9 — pytania: quality gate między dwoma repo, `pull_request` vs `pull_request_target`, wstrzyknięcie przez nazwę gałęzi, flaky test w bramce, jak powstaje wymagany status.
- [ ] **Step 3: `CLAUDE.md` i `docs/komendy.md`:** status („Etap 5A zrobiony <data>, następne 5B”), jedno zdanie o bramce w repo sklepu i o gałęzi o tej samej nazwie.
- [ ] **Step 4: Sprawdź:** `uv run ruff check`, `uv run ruff format --check`, `uv run pytest` (150 passed). Commit; bez pushu.
- [ ] **Step 5: Zapytaj o zgodę na push gałęzi `etap-5a-bramka-sklepu` i PR do `main` repo testów.** Po zgodzie push i `gh pr create`; scala właściciel.
