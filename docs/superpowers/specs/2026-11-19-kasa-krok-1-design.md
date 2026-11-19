# Kasa, krok 1: dopasowanie testów do nowej kasy — projekt

Data: 2026-11-19. Rozmiar: mała zmiana. Gałąź: `feat/payu` (ta sama nazwa co w repo sklepu, para gałęzi z ADR-016).

## Po co

Sklep na `feat/payu` dostał kasę (`/kasa`, kody rabatowe, dostawy, PayU). Obecny zestaw na tej gałęzi: 144 passed, 6 failed. Wszystkie 6 porażek wynika z zamierzonych zmian w sklepie, nie z błędów. Dopóki testy z `main` ich nie znają, PR sklepu jest czerwony. Krok 1 dopasowuje te 6 testów, żeby para gałęzi mogła się scalić. Nowe testy kasy to krok 2.

## Podejścia

- **A. Jedna para gałęzi ze wszystkim** (dopasowanie i nowe testy kasy). Odrzucone: PR sklepu czekałby na całość, a błąd znaleziony przez nowe testy zatrzymałby parę (ADR-014).
- **B. Dwa kroki** (wybrane przez właściciela 2026-11-19). Krok 1: tylko dopasowanie, mały PR w parze. Krok 2: nowe testy kasy na osobnej gałęzi, po scaleniu kasy na `main` sklepu.

## Co się zmieniło w sklepie i co robimy

| Test | Przyczyna porażki | Dopasowanie |
|---|---|---|
| K-02, K-03 (kontrakt koszyka) | Koszyk ma dwa nowe pola, zawsze obecne: `discountCode` (tekst, pusty bez kodu) i `discountAmount` (liczba całkowita, 0 bez kodu) | Oba pola w `schemas/cart.json` jako wymagane, `discountAmount` z `minimum: 0`. `additionalProperties: false` zostaje |
| A-ORD-05, D-ORD-05, D-ORD-06 (zamówienie ponad stan) | Koszyk odrzuca ilość ponad stan rozmiaru już przy dodaniu, więc koszyk ponad stan nie powstaje | Brak stanu przy zamówieniu da się nadal wywołać: klient A ma w koszyku ostatnią sztukę, klient B kupuje ją pierwszy, zamówienie A dostaje „Brak stanu”. Testy dostają ten scenariusz (dwie sesje z `make_shop`). D-ORD-05 i D-ORD-06 sprawdzają, że zamówienie A nie zostawia wiersza ani nie zmienia stanu ponad to, co zabrało zamówienie B |
| E-01 (zakup w przeglądarce) | Formularz `/kasa`: osobno Imię i Nazwisko, wymagany regulamin, wybór dostawy, przycisk „potwierdzam zakup” | `CheckoutPage` dostaje nowe pola i kroki. Dostawa: Kurier DPD. Suma na stronie zamówienia = cena produktu + 15 zł |

Nowy przypadek: **A-CART-14**, koszyk nie przyjmuje ilości ponad stan rozmiaru: „Dostępnych jest N szt.”, przy zerowym stanie „Brak stanu”, koszyk bez zmian. To nowa reguła, przez którą padły stare testy, więc dostaje własny test w tym kroku. Szycia na miarę limit nie dotyczy, bo stan się wtedy nie zmienia (R1).

## Wymagania i macierz śledzenia

- **R25** (spec kasy sklepu, 2026-11-17): koszyk nie przyjmuje ilości większej niż stan rozmiaru; szycie na miarę bez limitu. Pokrywa A-CART-14.
- **R26** (spec kasy sklepu, 2026-11-17, rozdział 3): suma zamówienia = produkty po rabacie + cena dostawy z listy sklepu. W kroku 1 pokrywa ją E-01 (bez kodu); rabaty i lista dostaw to krok 2.
- A-ORD-05, D-ORD-05, D-ORD-06: nowe tytuły (zamówienie przegrywa wyścig o ostatnią sztukę), dalej R17.
- Po zmianie: `uv run python scripts/build_traceability.py`, commit PDF razem z JSON-em.

## Cele, anty-cele

- **Cel:** na `feat/payu` sklepu pełny zestaw zielony, 4 procesy, testy niezależne. Bramka na PR sklepu `feat/payu` zielona z gałęzią testów `feat/payu`.
- **Anty-cel:** osłabienie testu, żeby przeszedł (np. usunięcie sprawdzania „Brak stanu” przy zamówieniu albo `additionalProperties: true`).

## Poza zakresem (krok 2)

Nowe pole `checkout` w `POST /api/commerce/orders` i jego walidacja, kody rabatowe (`/api/commerce/discount`, `/api/admin/discount-codes`), lista dostaw i kraj, odpis zamówienia w bazie (`checkoutJson`), PayU z kwotą, E2E z kodem. Stary kształt zamówienia (`email` + `shipping`) nadal działa w API i testy API dalej go używają; czy zostaje na stałe, to pytanie do kroku 2.

## Dokumenty

`KNOWLEDGE.md`: sekcja 2 (Etap „Kasa”, krok 1), sekcja 6 (problem: sklep nie startował na pustej bazie, poprawka po stronie sklepu), sekcja 8 (kroki), sekcja 9 (pytanie: test, który pada przez zamierzoną zmianę, a test, który pada przez błąd). `CLAUDE.md`: status.

## Co zostaje wykonawcy

Nazwy pól formularza w `CheckoutPage` (z etykiet strony), dane testowe kupującej (imię i nazwisko osobno), dokładny lokator sumy na stronie zamówienia, jeśli obecny łapie kilka kwot.
