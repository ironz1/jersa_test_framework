# Etap 5A — Bramka testów na PR sklepu: projekt

> **Wynik (2026-11-17):** cel „czerwony test = zablokowany Merge” nie jest osiągalny na darmowym planie GitHuba dla prywatnego repo (reguła ochrony zapisana, ale nieegzekwowana). Bramka działa jako informacyjna; egzekwowanie wrócą w 5B albo po zakupie planu Pro. Szczegóły: ADR-016 w `KNOWLEDGE.md`.

Data: 2026-11-17. Rozmiar: projekt (jedno workflow w innym repo, ale z decyzjami o bezpieczeństwie i o współpracy dwóch repo).

## Po co

Dziś zmiany w sklepie trafiają na `main` i od razu na Vercel, a testy uruchamia się ręcznie. Chcemy, żeby **błąd sklepu wychodził przed scaleniem**: PR do `main` sklepu buduje sklep z kodu PR-a, uruchamia cały zestaw testów z repo testów i zgłasza status. Status zablokuje Merge (reguła ochrony ustawiona ręcznie przez właściciela). To odpowiedź na temat rozmowy „quality gate i CI/CD” i główny trigger z ADR-005.

## Zakres tego kroku (5A)

- Workflow `.github/workflows/tests.yml` w repo **sklepu**, wyzwalany przez `pull_request` do `main`.
- Zadanie o nazwie `tests` (to nazwa statusu, który właściciel wskaże w regule ochrony).
- Notatka dla agenta sklepu w `AGENTS.md` (zrobione 2026-11-17, niezacommitowane).
- Dokumentacja po stronie repo testów: ADR-016, sekcja 3 (CI), pytania rekrutacyjne.

## Poza zakresem (kolejne kroki Etapu 5)

- **5B:** job w repo testów na `push`/`pull_request` z `main` sklepu (wymaga tokena do prywatnego repo sklepu), nightly na STG, smoke po deployu, wybór narzędzia raportów (pytest-html czy Allure).
- Gotowy obraz w GHCR, przyspieszanie budowy.
- Reguła ochrony: ustawia ją właściciel w GitHubie po pierwszym zielonym przebiegu (nazwa statusu pojawia się na liście dopiero wtedy).
- Zmiany w kodzie sklepu poza plikiem workflow i `AGENTS.md`.

## Przebieg workflow (decyzje)

1. **Wyzwalacz:** `on: pull_request: branches: [main]`. `concurrency` po nazwie gałęzi z `cancel-in-progress: true` (nowy push do PR-a przerywa stary przebieg).
2. **Sklep:** `actions/checkout` PR-a (commit scalający z `main`) do `shop/`.
3. **Testy:** repo `ironz1/jersa_test_framework` jest **publiczne**, więc checkout **bez tokena** (zamyka otwartą decyzję o mechanizmie: checkout w workflow sklepu, bez `repository_dispatch`). Wybór gałęzi testów: jeśli w repo testów istnieje gałąź o **tej samej nazwie** co gałąź PR-a sklepu, użyj jej, w przeciwnym razie `main` (wariant B z rozmowy). Sprawdzenie przez `git ls-remote --heads` na adresie publicznego repo.
4. **Środowisko:** `astral-sh/setup-uv@v10.3.3`, `uv sync --locked`, `uv run playwright install --with-deps chromium`.
5. **Sklep w Dockerze:** `docker compose up -d --build --wait` uruchamiany w katalogu `tests/` z `STOREFRONT_PATH` wskazującym `shop/`. Obraz budowany przy każdym przebiegu, **bez cache w pierwszej wersji**; zmierzyć czas i dopiero wtedy optymalizować.
6. **Konfiguracja testów:** zmienne środowiskowe `BASE_URL=http://127.0.0.1:3100` i `DATABASE_URL=postgresql://jersa:jersa@127.0.0.1:5432/jersa` ustawione w kroku (bez `.env`).
7. **Testy:** `uv run pytest --tracing retain-on-failure` (cały zestaw, `-n 4` z `addopts`; jeśli runner z 2 vCPU nie wytrzyma, ustawić `-n 2` tylko w CI i opisać w ADR).
8. **Artefakty (`if: always()`):** `test-results/` (ślady Playwrighta, nazwa z numerem przebiegu) i `docker compose logs` (przy porażce).
9. **Sprzątanie (`if: always()`):** `docker compose down -v`.
10. **Limit czasu** zadania: 20 minut (`timeout-minutes`).

## Bezpieczeństwo (wymagania)

- **Bez sekretów.** Workflow nie używa żadnego tokena poza domyślnym `GITHUB_TOKEN` z `permissions: contents: read`.
- **Nazwa gałęzi to dane wejściowe.** `github.head_ref` nigdy nie jest wstawiane do skryptu przez `${{ }}`; przekazujemy je zmienną środowiskową i cytujemy (ochrona przed wstrzyknięciem polecenia).
- Akcje przypięte do wersji (jak w `ci.yml`): `actions/checkout@v7`, `astral-sh/setup-uv@v10.3.3`, `actions/upload-artifact` w wersji sprawdzonej przez `gh api .../git/ref/tags/<tag>`.
- Repo sklepu jest prywatne, więc PR-y z forków nie występują; mimo to workflow nie uruchamia kodu z `pull_request_target`.

## Cele, anty-cele

- **Cel:** czerwony test = zablokowany Merge, zielony = Merge możliwy; przebieg < 15 minut; po porażce artefakty wystarczają do diagnozy bez uruchamiania lokalnie.
- **Anty-cel:** bramka, która jest czerwona z powodów niezwiązanych ze zmianą (flaky test, brak sprzątania po poprzednim przebiegu). Dlatego każdy przebieg startuje na czystej bazie, a po zadaniu `down -v`.

## Weryfikacja

- Lokalnie, przed pushem: `actionlint` (jeśli dostępny) albo parser YAML; kroki 5–7 odtworzone ręcznie z `STOREFRONT_PATH` wskazującym klon sklepu (to już robimy codziennie).
- Pierwszy przebieg na PR-ze dodającym workflow (workflow z PR-a uruchamia się na tym samym PR-ze): zielony, zapisany czas każdego kroku.
- Kontrola czerwieni: PR testowy (lub gałąź z celowo złą zmianą w sklepie) pokazuje czerwony status i artefakty; potem reguła ochrony i sprawdzenie, że Merge jest zablokowany.

## Co zostaje wykonawcy

Dokładna składnia kroków i nazwy artefaktów, sposób odczytu istnienia gałęzi (`git ls-remote`), ustawienie `-n` w CI po pomiarze, kolejność kroków sprzątania.

## Dokumenty po zmianie (repo testów)

`KNOWLEDGE.md`: ADR-016 (checkout publicznych testów bez tokena, gałąź o tej samej nazwie, obraz budowany bez cache), sekcja 3 „CI — konfiguracja w GitHubie” (poprawka: repo testów jest publiczne, token niepotrzebny), sekcja 8 (kroki), sekcja 9 (pytania: bramka cross-repo, wstrzyknięcie przez nazwę gałęzi, flaky w bramce, `pull_request` vs `pull_request_target`), `CLAUDE.md` (status). Sam plik `tests.yml` żyje w repo sklepu.
