# Seed bez produktów podglądu — projekt

Data: 2026-11-20. Rozmiar: mała zmiana. Gałąź: `feat/seed-live-catalog`, w parze z gałęzią sklepu o tej samej nazwie (ADR-016). Gałęzi nie scalamy; PR otwiera właściciel.

## Po co

Seed bazy sklepu nie wstawia już pięciu produktów podglądu (`zakiet-castello`, `bluzka-greta`, `sukienka-mandy`, `suknia-mandisa`, `komplet-zakiet-bacan`). Na pustej bazie wstawia 59 produktów z katalogu na żywo. Testy i healthcheck, które czytają produkt z seeda, muszą przejść na produkt, który w nowym seedzie jest. Bez tego healthcheck Dockera pada, zanim ruszy pytest.

## Podejścia

- **Wybrane:** jedno miejsce na założenia o seedzie, moduł `jersa/seed.py` (slug, nazwa w bazie, fraza wyszukiwania, fragment sluga). Przy następnej zmianie seeda poprawia się jeden plik.
- Odrzucone: podmiana napisów w każdym pliku. Mniejsza zmiana, ale te same założenia zostają rozsiane po dziesięciu plikach.

## Produkt dowodowy

`sukienka-stella`: widoczny, nazwa w bazie „SUKIENKA  STELLA” (dwie spacje), 460 zł, rozmiary 34–44, kategoria sukienki, szycie na miarę. Ta sama nazwa ma też `sukienka-stella1`, więc wyszukiwanie „stella” zwraca dwa produkty. E2E wybiera wynik po slugu w adresie linku, nie po nazwie. Nazwa dostępna linku ma spacje zliczone do jednej, więc wzorce nazw w page objectach przyjmują dowolny odstęp. Nagłówek strony produktu porównuje dokładną nazwę z bazy. Fragment sluga do wyszukiwania: `ka-stel` (jest w slugu, nie ma go w nazwie).

## Zmiany

- `docker-compose.yml`: healthcheck szuka `stella` i czeka na `sukienka-stella`.
- Testy: `tests/db/test_seed_smoke.py`, `tests/api/test_search.py`, `tests/api/test_wishlist.py`, `tests/contract/test_wishlist_contract.py`, `tests/contract/test_search_contract.py`, `tests/db/test_session_rows_db.py`, `tests/e2e/test_search_e2e.py`, `tests/e2e/test_product_page_smoke.py`, `tests/e2e/test_cart_e2e.py`, `tests/e2e/test_wishlist_e2e.py`.
- Bez zmian: opinie CASTELLO (A-REV-01, K-05; seed dalej wstawia te opinie), przykład sluga w `tests/framework/test_own_product.py`, testy z własnym produktem (ADR-012).
- Dokumenty: sekcja seeda w `docs/api-reference.md`, tytuł D-01 w macierzy, opisy obecnego stanu w `KNOWLEDGE.md` (dziennik historyczny zostaje), status w `CLAUDE.md`.

## Sprawdzenie

Sklep zbudowany z drzewa roboczego gałęzi sklepu na pustej bazie (`docker compose down -v`, potem `up --build --wait`). Healthcheck zielony i pełny `uv run pytest` zielony.
