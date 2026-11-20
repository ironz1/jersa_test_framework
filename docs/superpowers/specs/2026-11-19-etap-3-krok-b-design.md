# Etap 3, krok B: testy walidacji wejścia API sklepu — projekt

Data: 2026-11-19. Rozmiar: mała zmiana. Gałąź: `etap-3-krok-b` od `main` repo testów (poprawki są już na `main` sklepu, para gałęzi niepotrzebna).

## Po co

W kroku A Etapu 3 (2026-11-13) testy objęły tylko zachowania, które sklep miał poprawnie. Walidacja wejścia w `/api/commerce/*` czekała na poprawkę w sklepie, a testy zachowań do poprawy nie trafiają do publicznego repo przed poprawką (ADR-014). Poprawka jest na `main` sklepu (`b5e32c3`), sprawdzona sondą 2026-11-19 na Dockerze: wszystkie poniższe zachowania działają. Krok B dodaje ich testy, żeby bramka pilnowała ich na każdym PR-ze sklepu.

## Podejścia

Jedna sensowna droga: testy dopisane do istniejących plików wg obszaru (`test_cart.py`, `test_orders.py`, `test_checkout.py`, `test_wishlist.py`, `test_reviews.py`, `test_orders_db.py`) i jeden nowy plik na uszkodzony JSON przez wszystkie endpointy (parametryzacja). Osobny plik „walidacja” dla wszystkiego odrzucony: rozbiłby reguły jednego obszaru na dwa miejsca.

## Zachowania do testów (zatwierdzone przez właściciela 2026-11-12/13, sprawdzone sondą 2026-11-19)

| Obszar | Wejście | Oczekiwane |
|---|---|---|
| Ilość w koszyku | `POST`: -1, 0, 1.5, `"abc"` | 400 „Nieprawidłowa ilość”, koszyk bez zmian |
| | `PATCH`: -1, 1.5, `"abc"` | to samo; `PATCH` z 0 nadal usuwa pozycję (A-CART-09) |
| Produkt i rozmiar | produkt nieistniejący albo ukryty | 400 „Nie znaleziono produktu” |
| | rozmiar spoza listy produktu | 400 „Nieprawidłowy rozmiar” |
| | szycie na miarę dla produktu bez miary | 400 „Produkt nie jest dostępny na miarę” |
| | `customFit: true` ze zwykłym rozmiarem | 400 „Nieprawidłowy rozmiar” |
| Pozycja koszyka | `PATCH` nieznanego `lineId` | 400 „Nie znaleziono pozycji”; `DELETE` nieznanej pozycji 200 |
| Dane zamówienia (oba kształty: `email`+`shipping` i `checkout`) | e-mail bez formatu `nazwa@domena.pl`, kod pocztowy spoza `00-000`, telefon nie z 9 cyfr | 400 „Nieprawidłowy e-mail” / „Nieprawidłowy kod pocztowy” / „Nieprawidłowy telefon” |
| | telefon z `+48`, spacjami albo myślnikami | przyjęty |
| | kod pocztowy drugiego adresu spoza `00-000` | 400 „Nieprawidłowy kod pocztowy wysyłki” |
| Ukryty produkt | ukryty po dodaniu do koszyka, potem zamówienie | 400 „Produkt niedostępny”, koszyk i stan bez zmian, brak zamówienia w bazie |
| | opinia do ukrytego produktu | 400 „Nie znaleziono produktu” |
| Lista życzeń | produkt nieistniejący albo ukryty | 400 „Nie znaleziono produktu” |
| Uszkodzony JSON | `POST/PATCH/DELETE /cart`, `POST /orders`, `POST /payu/start`, `POST/DELETE /wishlist`, `POST /reviews`, `POST /discount` | 400 „Nieprawidłowe dane” (kształt `error.json`) |
| | `POST /payu/notify` | 400 „Brak zamówienia” (endpoint czyta surową treść do podpisu PayU; notatka dla sklepu dopuszczała własne komunikaty) |

Poza zakresem: tryb płatności i podpis powiadomienia.

## Zasady

- Własny produkt na każdy test (`make_product(made_to_measure=False)`, `hidden=True`); ukrycie po dodaniu do koszyka przez SQL na własnym produkcie (nowa funkcja `set_hidden(conn, slug, hidden)` w `jersa/db/products.py`).
- Uszkodzony JSON wysyłany surowym `data=` z nagłówkiem `Content-Type: application/json` przez `ApiClient` (bez nowej metody w `CommerceApi`).
- Każdy test: `regression`, docstring od ID, wpis w macierzy. Nowe wymagania od R35 ze źródłem „właściciel sklepu, 2026-11-12/13”. Uszkodzony JSON pod istniejące R13.
- Po scaleniu: lista scenariuszy Etapu 3 (`docs/scenariusze-etap-3.md`, dziś wykluczona z gita) może być opublikowana, bo opisane w niej słabości są poprawione. Decyzja właściciela przed usunięciem wykluczenia.

## Dokumenty

Macierz (R35+, przypadki), `KNOWLEDGE.md` (sekcja 2: Etap 3 krok B zamknięty; sekcja 8; sekcja 9: pytanie o testy walidacji wejścia i wartości graniczne), `CLAUDE.md` (status).
