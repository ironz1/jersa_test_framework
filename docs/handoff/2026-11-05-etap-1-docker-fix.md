# Zadanie dla repo jersa-storefront: naprawa builda obrazu Docker

- **Od:** repo testów `jersa_test_framework`
- **Data:** 2026-11-05
- **Poprzednie zadanie:** `docs\handoff\2026-11-01-etap-1-docker.md`

## Decyzja człowieka

Zatwierdzona jest opcja B w węższym zakresie: `force-dynamic` tylko na `/blog` i `/szycie-na-miare`. Obraz ma się budować bez dostępu do bazy, a te strony mają czytać dane w czasie działania.

## Zadanie

Commit lokalny, **bez pusha**.

1. `src/app/blog/page.tsx`: zastąp `export const revalidate = 60` przez `export const dynamic = "force-dynamic"`.
2. `src/app/szycie-na-miare/page.tsx`: dodaj `export const dynamic = "force-dynamic"`.
3. `Dockerfile`: popraw komentarz przy `next build`, żeby opisywał stan po tej zmianie. Obecny mówi, że strony oparte na Prismie obsługują brak bazy, a `/blog` tego nie robił.
4. Usuń pusty plik `{console.log(r)`.
5. Dopisz decyzję do Decision log w `CLAUDE.md` i do `docs/PLAN.md`.

## Czego nie zmieniać

- `/blog/[slug]`: zostają `revalidate = 60` i `generateStaticParams`. Ta trasa nie blokuje builda i czyta bazę przy pierwszym wejściu.
- Seed: wpisy bloga w seedzie to osobne, późniejsze zadanie.
- Logika aplikacji, UI i API poza punktami wyżej.
- Niezacommitowane strony (`faq`, `regulamin`, `cookies`, `polityka-prywatnosci`, `reklamacje`, `metody-platnosci`) i zmiany w stopce: nie włączaj ich do tego commita.

## Kryteria akceptacji

Wymagany jest dowód z uruchomienia, nie sam opis:

- `docker build --target runner .` przechodzi. Wklej ostatnie 15 linii wyniku.
- W tabeli tras z `next build` `/blog` i `/szycie-na-miare` są oznaczone jako dynamiczne (`ƒ`). Wklej te wiersze.
- `npx tsc --noEmit` bez błędów i `npx vitest run` zielony. Wklej podsumowanie.

Jeśli build pokaże kolejną stronę wymagającą bazy, zatrzymaj się i opisz ją. Nie dokładaj kolejnych zmian zachowania aplikacji bez zgody człowieka.

Jeśli `docker build` nie może się uruchomić, napisz to wprost i nie zgłaszaj zadania jako wykonanego.

## Po zakończeniu

Podsumuj: zmienione pliki, hash commita, wyniki kryteriów i informację, czy niezacommitowane strony są gotowe, czy czekają na decyzję człowieka.
