# Etap 3 — warstwy testów: projekt

- **Data:** 2026-11-13
- **Status:** zaakceptowany 2026-11-13
- **Wejście:** szkielet z Etapu 2 (4 testy smoke, fixtures, schematy, CI), sklep w Dockerze (`127.0.0.1:3100`), lista scenariuszy z potwierdzonymi regułami biznesowymi (roboczy plik lokalny, poza repo).

## Cel i po co

Pokryć testami najważniejszą ścieżkę sklepu (znalezienie produktu → koszyk → zamówienie → płatność) na czterech poziomach, tak żeby:

- **piramida** była widoczna w kodzie: dużo szybkich testów API, mniej DB, mało E2E;
- każdy poziom odpowiadał na inne pytanie: kontrakt — *jaki kształt ma odpowiedź*, API — *czy reguły działają*, DB — *czy dane naprawdę się zapisały*, E2E — *czy klient przejdzie ścieżkę w przeglądarce*;
- materiał dobrze pokazywał się na rozmowie (bazy danych, Python, quality gate w Etapie 5).

Właściciel sklepu uznał, że najważniejszy jest front (bez niego nie ma sklepu). Dlatego E2E obejmuje pełny zakup, ale reszta scenariuszy leży niżej w piramidzie, gdzie testy są szybsze i wskazują przyczynę.

## Zakres

W zakresie: `/api/commerce/*` (koszyk, zamówienia, płatność, opinie, przechowalnia, wyszukiwarka), tabele `OrderRow`, `ProductRow`, `ReviewRow`, ścieżka zakupu i wyszukiwania w przeglądarce.
Poza zakresem: panel admina, blog, strony informacyjne, Instagram, STG (Etap 5), równoległość (Etap 4).

## Liczby (cel)

| Poziom | Testów | Uwagi |
|---|---|---|
| Kontrakt | 9 | po jednym schemacie na odpowiedź, w tym błąd 400 |
| API | ok. 45 | koszyk, zamówienie, płatność, opinie, przechowalnia, wyszukiwarka |
| Baza | 10 | akcja przez API, wynik sprawdzony SQL-em |
| E2E | 5 | zakup, brak rozmiaru, wyszukiwanie, przechowalnia, strona produktu |

W tym 4 testy smoke już istnieją. Dokładna lista scenariuszy z oczekiwanymi wynikami jest w pliku scenariuszy.

## Decyzje

1. **Dwa kroki.** Krok A: testy zachowań, które sklep już ma poprawnie. Krok B: kolejne testy API, dopiero po zmianie w sklepie. *Dlaczego:* w publicznym repo nie zostawiamy testów opisujących otwarte luki, a `xfail` z opisem byłby takim opisem. *Alternatywa odrzucona:* piszemy wszystko od razu i oznaczamy `xfail`.
2. **Oczekiwany wynik z reguł biznesowych, nie z kodu.** Reguły potwierdził właściciel sklepu; test sprawdza regułę, nie to, co kod akurat robi.
3. **Testy względne wobec seeda.** Seed jeszcze się zmieni, więc test odczytuje stan przed akcją (np. stan magazynowy rozmiaru) i porównuje różnicę. Żadnych „5 sztuk” na sztywno.
4. **Własny produkt na test** (decyzja właściciela 2026-11-13). Fixture wstawia przez SQL własny `ProductRow` (`test-<uuid>`, własny stan, cena, opcjonalnie promocja), oddaje go testowi i po teście usuwa po ID razem z zamówieniami tego produktu. Opinie test dodaje do własnego produktu, więc znikają razem z nim. Seed jest tylko czytany (wyszukiwarka, opinie CASTELLO, strona produktu). *Dlaczego:* kilkanaście testów zamawia towar, a seed ma po 5 sztuk; testy mają przechodzić wielokrotnie bez `down -v`, nie zależeć od zmian seeda i działać równolegle. *Alternatywy odrzucone:* różne rozmiary z seeda (działa tylko na świeżej bazie, brak produktu z promocją), oddawanie stanu w teardownie (zmienia rekord seeda). *Koszt:* wstawianie przez SQL trzeba poprawić, gdy sklep doda kolumnę do `ProductRow`; testy zamówień wymagają `DATABASE_URL`. To zamyka otwartą decyzję „Strategia stanu magazynowego” z `KNOWLEDGE.md` i przenosi własne dane testu z Etapu 4 do Etapu 3; w Etapie 4 zostaje równoległość.
5. **Testy bazy sprawdzają skutek akcji z API.** SQL w fixture tylko przygotowuje własny produkt; sprawdzane zamówienie powstaje przez API. Pytanie na rozmowie: „skąd wiesz, że zapis naprawdę trafił do bazy”.
6. **Płatność w E2E.** E2E potwierdza płatność przez `POST /payu/notify`, tak jak robi to operator płatności. Gdy w sklepie pojawi się przycisk „Symuluj opłacenie”, test przejdzie na kliknięcie: test ma wykonywać ten sam krok co klient.
   `PAYU_MODE: mock` trafia do `docker-compose.yml` już w kroku A.
7. **Krok B ma osobny plan**, pisany po zmianie w sklepie. Wtedy znane będą ostateczne komunikaty błędów; testy sprawdzają status 400 i dokładny komunikat.
8. **Page objecty** dla E2E: `ProductPage` (rozszerzony), koszyk, kasa, strona zamówienia, wyszukiwarka. Selektory po roli i etykiecie, nie po klasach CSS. Konkretne selektory ustala plan na podstawie istniejących testów E2E sklepu.

## Struktura (zmiany względem Etapu 2)

```
tests/{contract,api,db,e2e}/        # nowe pliki wg obszaru: test_cart_*, test_orders_*, ...
schemas/                            # nowe: cart, wishlist, reviews, order, payu-start, payu-notify, error
src/jersa/fixtures/products.py      # własny produkt testu + sprzątanie po ID
src/jersa/fixtures/orders.py        # składanie zamówień + sprzątanie po ID
src/jersa/clients/commerce.py       # jedna metoda na endpoint sklepu
src/jersa/db/{products,orders}.py   # SQL własnego produktu i odczyt zamówień
src/jersa/pages/                    # nowe page objecty
```

Markery: `smoke` (ścieżka krytyczna na każdym poziomie), `regression` (reszta), `contract` (kontrakt). Zgodnie z konwencją piramidy E2E ma najmniej testów.

## Kryteria akceptacji

- Krok A: wszystkie testy przechodzą na świeżym sklepie (`down -v`, `up --build --wait`); `ruff check` i `ruff format --check` bez uwag; `pytest tests/framework` zielone w CI.
- Każdy test jest niezależny: przechodzi uruchomiony osobno i w dowolnej kolejności.
- Po przebiegu w bazie nie zostają produkty, zamówienia ani opinie testów; stan magazynowy produktów z seeda jest taki sam jak przed przebiegiem.
- Zestaw przechodzi trzy razy z rzędu bez `down -v`.
- Czerwony test pokazuje czytelny powód (ścieżka w schemacie, oczekiwana i faktyczna wartość).
- Krok B: ten sam komplet kryteriów, po zmianie w sklepie.

## Czego zrobi plan, a czego nie ustalam tutaj (decyzje wykonawcy)

Dokładne nazwy plików i fixtures, kształt schematów (spisane z realnych odpowiedzi), selektory E2E, podział na zadania.

## Zapisy w dokumentacji (w ramach etapu)

ADR dla decyzji 1, 3 i 4 (decyzja 4 zamyka otwartą decyzję o stanie magazynowym) w `KNOWLEDGE.md` (z wypełnionym polem „Na rozmowie”), pytania rekrutacyjne w sekcji 9 (bazy danych, Python, piramida), kroki w sekcji 8, aktualizacja `docs/api-reference.md` o `DELETE /api/commerce/wishlist`.

## Moje decyzje do sprawdzenia (nie ustalone z właścicielem)

- Podział na krok A i B oraz zamiast `xfail` odłożenie testów B.
- Kolejność: kontrakt → API → baza → E2E.
- Liczby testów w tabeli (cel, nie limit).
- Po recenzji (2026-11-13): `PAYU_MODE` w compose już w kroku A, osobny plan kroku B.
