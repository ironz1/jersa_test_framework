"""Założenia testów o danych z seeda sklepu: jeden produkt dowodowy, tylko do czytania.

Testy, które coś kupują albo zmieniają, biorą własny produkt (ADR-012). Ten produkt służy
tylko testom, które sprawdzają, że seed przeszedł: wyszukiwarka, strona produktu,
przechowalnia. Gdy seed się zmieni, poprawia się ten plik.
"""

SEED_SLUG = "sukienka-stella"
# Nazwa dokładnie jak w bazie, z dwiema spacjami.
SEED_NAME = "SUKIENKA  STELLA"
# Fraza z nazwy. Trafia też `sukienka-stella1` o tej samej nazwie.
SEED_QUERY = "stella"
# Fragment sluga, którego nie ma w nazwie: sprawdza szukanie po slugu.
SEED_SLUG_FRAGMENT = "ka-stel"
