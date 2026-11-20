"""Własny produkt testu w tabeli `ProductRow`: wstawienie, odczyt stanu i sprzątanie.

Test nie rusza produktów z seeda. Dostaje własny produkt ze slugiem `test-<hex>`,
a po teście znika on razem ze swoimi zamówieniami i opiniami.
"""

import json
import uuid
from dataclasses import dataclass

import psycopg
from psycopg import sql

OWN_PREFIX = "test-"
DEFAULT_STOCK = {"36": 5, "38": 5}


def new_slug() -> str:
    return OWN_PREFIX + uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class OwnProduct:
    slug: str
    name: str
    amount: int
    promo_percent: int
    stock: dict[str, int]

    @property
    def price(self) -> int:
        """Cena sprzedaży w pełnych złotych: cena katalogowa pomniejszona o procent promocji,
        połówki zaokrąglane w górę."""
        return (self.amount * (100 - self.promo_percent) + 50) // 100


def product_row(
    slug: str,
    *,
    name: str | None = None,
    amount: int = 200,
    stock: dict[str, int] | None = None,
    promo_percent: int = 0,
    made_to_measure: bool = True,
    hidden: bool = False,
) -> dict[str, object]:
    """Wiersz `ProductRow` jako słownik kolumna → wartość. Kolumny JSON to tekst, jak w sklepie."""
    sizes = dict(DEFAULT_STOCK) if stock is None else stock
    return {
        "id": slug,
        "slug": slug,
        "shoperId": 0,
        "name": name or f"Produkt testowy {slug.removeprefix(OWN_PREFIX)}",
        "amount": amount,
        "description": "Produkt testowy frameworka.",
        "opisJson": json.dumps(
            {
                "intro": "Produkt testowy.",
                "features": ["test"],
                "sizesNote": "36–38",
                "material": "test",
            },
            ensure_ascii=False,
        ),
        "imagesJson": json.dumps([{"src": "/preview/outfits/3.jpg", "alt": "Produkt testowy"}]),
        # Pusta lista kategorii: produkt nie pojawia się w kategoriach ani na stronie głównej.
        "categorySlugs": "[]",
        "sizeCodes": json.dumps(list(sizes)),
        "unavailable": json.dumps([code for code, quantity in sizes.items() if quantity <= 0]),
        "madeToMeasure": made_to_measure,
        "isNew": False,
        "isPromo": promo_percent > 0,
        "promoPercent": promo_percent,
        "lowestPriorAmount": 0,
        "offeredLessThan30Days": False,
        "isBestseller": False,
        "hidden": hidden,
        "stockBySize": json.dumps(sizes),
        "sizeChartSrc": "",
        "sortOrder": 9999,
        "relatedSlugs": "[]",
        "lookImagesJson": "[]",
    }


def insert_product(conn: psycopg.Connection, row: dict[str, object]) -> None:
    """Jawna lista kolumn: nowa kolumna sklepu z wartością domyślną nie psuje wstawiania."""
    query = sql.SQL('INSERT INTO "ProductRow" ({}) VALUES ({})').format(
        sql.SQL(", ").join(sql.Identifier(column) for column in row),
        sql.SQL(", ").join(sql.Placeholder() * len(row)),
    )
    conn.execute(query, list(row.values()))


def lines_pattern(slug: str) -> str:
    """Wzorzec LIKE dla `OrderRow.linesJson`: zamówienia zawierające ten produkt."""
    return f'%"productSlug":"{slug}"%'


def _require_own(slug: str, action: str) -> None:
    """Odmawia zmiany produktu bez prefiksu `test-`: pomyłka w teście nie ruszy danych seeda."""
    if not slug.startswith(OWN_PREFIX):
        raise ValueError(f"Odmowa {action}: '{slug}' nie jest produktem testu ({OWN_PREFIX}…)")


def set_hidden(conn: psycopg.Connection, slug: str, hidden: bool) -> None:
    """Ukrywa albo pokazuje własny produkt w sklepie (kolumna `hidden`)."""
    _require_own(slug, "ukrycia")
    conn.execute('UPDATE "ProductRow" SET hidden = %s WHERE slug = %s', (hidden, slug))


def delete_product(conn: psycopg.Connection, slug: str) -> None:
    """Usuwa własny produkt razem z jego zamówieniami i opiniami (tylko produkt testu)."""
    _require_own(slug, "usunięcia")
    conn.execute('DELETE FROM "OrderRow" WHERE "linesJson" LIKE %s', (lines_pattern(slug),))
    conn.execute('DELETE FROM "ReviewRow" WHERE "productSlug" = %s', (slug,))
    conn.execute('DELETE FROM "ProductRow" WHERE slug = %s', (slug,))


def read_stock(conn: psycopg.Connection, slug: str) -> dict[str, int]:
    row = conn.execute('SELECT "stockBySize" FROM "ProductRow" WHERE slug = %s', (slug,)).fetchone()
    if row is None:
        raise LookupError(f"Brak produktu '{slug}' w bazie")
    return json.loads(row["stockBySize"])
