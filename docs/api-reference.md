# jersa-storefront — referencja API (BFF) i dane testowe

> Materiał z Etapu 0, punkt wyjścia dla schematów kontraktów i testów API. Od Etapu 2 aktualny kształt odpowiedzi opisują schematy w `schemas/` (patrz sekcja 7).
> Zakres: `/api/commerce/*`. Admin (`/api/admin/*`) i `/media/[id]` są poza tym etapem.

## Zasady ogólne

- Katalog (home, PDP, kategorie) to React Server Components — **brak REST GET produktu**. Kontrakt API obejmuje tylko BFF poniżej.
- Ciasteczka (httpOnly, `path=/`, `SameSite=Lax`):

  | Cookie | Rola |
  |---|---|
  | `jersa_cart` | UUID koszyka, tworzone przy pierwszym GET/POST cart |
  | `jersa_wish` | UUID przechowalni (wishlist) |

- Błędy: `{ "error": "<polski string>" }`, status **400** (409 tylko na admin slug).

## Endpointy

| # | Metoda | Ścieżka | Wynik |
|---|---|---|---|
| 1 | GET | `/api/commerce/cart` | CartView |
| 2 | POST | `/api/commerce/cart` | CartView |
| 3 | PATCH | `/api/commerce/cart` | CartView |
| 4 | DELETE | `/api/commerce/cart` | CartView |
| 5 | GET | `/api/commerce/wishlist` | Wishlist |
| 6 | POST | `/api/commerce/wishlist` | Wishlist |
| 7 | GET | `/api/commerce/search?q=` | `{ products: Product[] }` |
| 8 | GET | `/api/commerce/reviews?productSlug=` | `{ reviews: Review[] }` |
| 9 | POST | `/api/commerce/reviews` | `{ reviews: Review[] }` |
| 10 | POST | `/api/commerce/orders` | `{ order: { id, publicToken } }` |
| 11 | POST | `/api/commerce/payu/start` | `{ ok, redirectUrl }` / `{ ok: false, reason }` |
| 12 | POST | `/api/commerce/payu/notify` | `{ ok, duplicate }` |

### 1. GET /api/commerce/cart

Pusty koszyk (nowe ciasteczko):

```json
{ "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7", "lines": [] }
```

### 2. POST /api/commerce/cart

Body:

```json
{ "productSlug": "zakiet-castello", "size": "36", "quantity": 1, "customFit": false }
```

- `size` wymagany (`""` → `"Wybierz rozmiar"`).
- `customFit: true` + `size: "made-to-measure"` → dopłata 100 zł, bez dopłaty rozmiarowej.

Przykład 200 (CASTELLO 350 zł, rozmiar 36, stan 5):

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "lines": [
    {
      "id": "zakiet-castello:36:std:0",
      "productSlug": "zakiet-castello",
      "size": "36",
      "quantity": 1,
      "customFit": false,
      "sizeSurcharge": 0,
      "product": {
        "id": "596",
        "slug": "zakiet-castello",
        "shoperId": 596,
        "name": "Żakiet CASTELLO",
        "price": { "amount": 350, "currency": "PLN", "formatted": "350,00 zł" },
        "description": "Żakiet CASTELLO — żakard, forma atelier.",
        "opis": {
          "intro": "Żakiet CASTELLO z tkaniny żakardu ecru z wplecioną złotą nitką.",
          "features": ["taliowany krój", "zapięcie na guzik", "długi rękaw", "na podszewce", "dekoracyjne kieszonki wystające poza długość żakietu"],
          "sizesNote": "34–56 oraz XS–5XL. Opcja szycia na miarę.",
          "material": "98% poliester, 2% elastan"
        },
        "images": [
          { "src": "/preview/outfits/3.jpg", "alt": "Żakiet CASTELLO — look (podmień docs/design/outfits/3.jpg)" },
          { "src": "/preview/outfits/5.jpg", "alt": "Żakiet CASTELLO — wariant (podmień docs/design/outfits/5.jpg)" }
        ],
        "categorySlugs": ["zakiety-bolerka"],
        "sizes": [{ "code": "34", "available": true }, { "code": "36", "available": true }],
        "madeToMeasure": true,
        "isNew": false,
        "isPromo": true,
        "isBestseller": true,
        "hidden": false,
        "sizeChartSrc": null,
        "relatedSlugs": []
      }
    }
  ]
}
```

Uwagi do schematu:
- `sizes` w seedzie CASTELLO to pełna lista 34–56 + XS–5XL; w jsonschema: tablica obiektów `{code, available}`.
- `sizeSurcharge` zależy od `ShopSetting` (domyślnie 0).
- `customFit` i `sizeSurcharge` bywają **opcjonalne** na starych liniach.

### 3. PATCH /api/commerce/cart

```json
{ "lineId": "zakiet-castello:36:std:0", "quantity": 2 }
```

→ ten sam CartView. Brak `lineId`/`quantity` → `"Brak linii"`.

### 4. DELETE /api/commerce/cart

```json
{ "lineId": "zakiet-castello:36:std:0" }
```

→ koszyk bez tej linii.

### 5. GET /api/commerce/wishlist

```json
{ "slugs": [], "products": [] }
```

### 6. POST /api/commerce/wishlist

```json
{ "productSlug": "zakiet-castello" }
```

→ `{ "slugs": ["zakiet-castello"], "products": [ /* Product jak wyżej */ ] }`

### 7. GET /api/commerce/search?q=castello

```json
{ "products": [ /* Product CASTELLO */ ] }
```

- Pusty `q` zwraca pustą listę.
- **Product ma dziś 22 pola** (stan 2026-11-06, zgodnie z `src/commerce/types.ts` sklepu). Przykład w sekcji 2 jest z Etapu 0 i nie zawiera nowszych pól: `compareAtPrice` (`Money | null`), `promoPercent`, `lookImages`, `lowestPriorAmount`, `offeredLessThan30Days`.
- **Źródło prawdy o kształcie odpowiedzi to schematy w `schemas/`** (`search.json`, `product.json`), sprawdzane testem `tests/contract/test_search_contract.py`. Gdy ten dokument i schemat się różnią, rację ma schemat.

- Puste `q` → `{ "products": [] }`.
- Szuka w `name` i `slug` (lowercase). Ukryte produkty odpadają.

### 8. GET /api/commerce/reviews?productSlug=zakiet-castello

```json
{
  "reviews": [
    { "id": "rev-castello-1", "productSlug": "zakiet-castello", "author": "Paulina", "body": "Elegancja i klasa." },
    { "id": "rev-castello-2", "productSlug": "zakiet-castello", "author": "Malwina", "body": "Idealny zestaw na komunię." }
  ]
}
```

Bez `productSlug` → `"Brak produktu"`.

### 9. POST /api/commerce/reviews

```json
{ "productSlug": "zakiet-castello", "author": "Anna", "body": "Leży świetnie." }
```

→ `{ "reviews": [ ...lista po dodaniu ] }`

- Puste imię → `"Podaj imię lub pseudonim"`.
- Pusta treść → `"Napisz opinię"`.

### 10. POST /api/commerce/orders

Wymaga ciasteczka koszyka z liniami. Body:

```json
{
  "email": "klientka@example.com",
  "shipping": {
    "name": "Anna Nowak",
    "street": "Piotrkowska 1",
    "city": "Łódź",
    "postalCode": "90-001",
    "phone": "500000000"
  }
}
```

200 — tylko id, nie pełne zamówienie:

```json
{
  "order": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "publicToken": "f0e1d2c3-b4a5-6789-0abc-def123456789"
  }
}
```

- Koszyk jest czyszczony, **stan magazynowy schodzi**.
- Pusty koszyk → `"Koszyk jest pusty"`. Brak stanu → `"Brak stanu"`.
- Timeout nieopłaconych: 30 min.

### 11. POST /api/commerce/payu/start

```json
{ "orderId": "<uuid z create>" }
```

| Sytuacja | Odpowiedź 200 |
|---|---|
| Mock, pierwszy start | `{ "ok": true, "redirectUrl": "/preview/platnosc?order=<orderId>" }` |
| Ponowny start (idempotencja) | ten sam `redirectUrl` |
| Zamówienie opłacone | `{ "ok": true, "redirectUrl": "/zamowienie/<publicToken>?paid=1" }` |
| Inny status | `{ "ok": false, "reason": "unavailable" }` |

### 12. POST /api/commerce/payu/notify

Mock bez podpisu:

```json
{ "orderId": "<uuid>", "extOrderId": "<uuid>", "status": "COMPLETED" }
```

- `status`: `COMPLETED` | `CANCELED` | `PENDING`.
- Odpowiedź: `{ "ok": true, "duplicate": false }`; drugi `COMPLETED` → `"duplicate": true`.

## Dane testowe (seed)

- Źródło: `fixtures/catalog.json` + `scripts/seed-catalog.ts`.
- Seed dopisuje brakujące slugi, **nie nadpisuje** edytowanych produktów. Opinie CASTELLO są upsert.
- Stan startowy: **5 szt. na każdy dostępny rozmiar**.

| slug | nazwa | cena | kategorie | MTM | new | promo | bestseller |
|---|---|---|---|---|---|---|---|
| `zakiet-castello` | Żakiet CASTELLO | 350 | zakiety-bolerka | tak | | tak | tak |
| `bluzka-greta` | Bluzka GRETA | 390 | bluzki | | | | tak |
| `sukienka-mandy` | Sukienka MANDY | 580 | sukienki | | | | tak |
| `suknia-mandisa` | Suknia MANDISA | 690 | sukienki, suknie | tak | tak | | |
| `komplet-zakiet-bacan` | Komplet żakiet BACAN | 1085 | komplety, komplety-damskie, zakiety-bolerka | | | | tak |

Rozmiary: CASTELLO 34–56 + XS–5XL; GRETA 34–40 + XS–L; MANDY / MANDISA / BACAN 34–40 + S–L.

**Stabilny happy path** (jak w e2e sklepu): CASTELLO rozmiar 36, email `klientka@example.com`, adres z `checkout.spec.ts`.

Landingi (wesele, nowosci, …) są w `catalog.json` i w `loadMeta()` OwnCommerce — nie w tabeli SQL.
