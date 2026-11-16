# Etap 4 — Równoległość (pytest-xdist): projekt

Data: 2026-11-16. Rozmiar: mała zmiana (krótki projekt, bez osobnego sprawdzenia przez recenzenta).

## Po co

Zestaw testów sklepu (83) i frameworka (65) ma działać szybko i, co ważniejsze, **udowodnić, że testy są niezależne**. Test, który przechodzi sam, a pada obok innych, ma ukrytą zależność. Równoległość ją ujawnia. To też temat rozmowy (Python, bazy danych): izolacja danych testowych.

## Cele

- `uv run pytest` domyślnie uruchamia testy na **4 procesach**, w tym E2E.
- Wszystkie testy sklepu i frameworka przechodzą na 4 procesach, wiele razy z rzędu.
- Po przebiegu baza jest czysta: seed bez zmian (md5), 0 koszyków, przechowalni, zamówień i produktów `test-*`.
- Czas przebiegu jest zmierzony przed i po, zapisany w `KNOWLEDGE.md`.

## Poza zakresem

- CI sklepu (Etap 5), liczba procesów dobierana do maszyny CI.
- Nowe testy, zmiany w sklepie, `pytest-randomly` i inne wtyczki.
- Odłożone drobiazgi z recenzji Etapu 3, chyba że padają przez równoległość.

## Podejścia

| | Jak | Wynik |
|---|---|---|
| A. Jawnie | `-n 4` w komendach i CI | odrzucone: łatwo zapomnieć o fladze |
| **B. `addopts`** | `-n 4` na stałe w `pyproject.toml` | **wybrane przez właściciela** |
| C. Zmienna `WORKERS` w `.env` | `Settings` i hook przed fixturami | odrzucone: więcej kodu na prosty cel |

Koszt wyboru B: debugowanie pojedynczego testu (`--pdb`) i podgląd na żywo (`HEADED=true`) wymagają `-n 0`. Bez tego `HEADED=true` otwiera 4 okna. Do opisania w `docs/komendy.md`, `README.md` i `.env.example` (przy `HEADED`).

## Decyzje (moje, do poprawienia)

- `pytest-xdist` w grupie `dev` (`uv add --dev pytest-xdist`), `-n 4` w `addopts`.
- Dystrybucja domyślna (`--dist load`). `loadfile` tylko wtedy, gdy wyjdą zależności w obrębie pliku, a to byłby błąd testu do naprawy, nie wygodny skrót.
- Naprawiamy przyczynę, nie objawy: test padający równolegle poprawiamy tak, by miał własne dane. Marker `serial` wprowadzamy tylko, gdy test z natury dotyka stanu globalnego, i opisujemy wyjątek w ADR.
- Fixtury `scope="session"` są per proces. Nie wymagają zmian, ale sprawdzamy, że baza i przeglądarka nie są współdzielone między procesami.
- Kolejność weryfikacji: (1) `-n 0` zielone (punkt odniesienia), (2) `-n 4` jeden przebieg, (3) naprawa padających, (4) 3 przebiegi z rzędu + kontrola stanu bazy.
- `tests/framework` (bez sklepu, w CI) działa też na 4 procesach. Jeśli start procesów wydłuży ten zestaw ponad czas jednoprocesowy, ustawiamy tam `-n 0` w `ci.yml`.

## Co zostaje wykonawcy

Wybór sposobu naprawy konkretnych kolizji, jeśli wystąpią. Podejrzani: wyszukiwanie „castello” (globalne wyniki, gdy inne testy wstawiają `test-*`), E2E na produkcie z seeda, kruchość E2E (brak sygnału hydracji, luźne lokatory).

## Dokumenty po zmianie

- `KNOWLEDGE.md`: odhaczyć Etap 3 i Etap 4 (sekcja 2), ADR-015 z polem „Na rozmowie”, krok w sekcji 8, pytania rekrutacyjne w sekcji 9 (izolacja testów równoległych, `-n`, `loadfile` vs `load`, fixtury sesyjne per proces).
- `CLAUDE.md`: status projektu i polecenia.
- `docs/komendy.md`, `README.md`, `.env.example`: `-n 0` do debugowania i podglądu.
