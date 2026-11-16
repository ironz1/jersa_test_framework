import pytest
from playwright.sync_api import expect

from jersa.clients.commerce import EMAIL, SHIPPING
from jersa.db.orders import order_id_by_token
from jersa.pages.checkout_page import CheckoutPage
from jersa.pages.order_page import URL_PATTERN, OrderPage
from jersa.pages.product_page import ProductPage


@pytest.mark.smoke
@pytest.mark.regression
def test_guest_buys_product(page, product, db, shop):
    """E-01: gość kupuje produkt od strony produktu do opłaconego zamówienia."""
    product_page = ProductPage(page)
    product_page.open(product.slug)
    product_page.choose_size("36")
    product_page.add_to_cart()
    expect(product_page.cart_drawer).to_be_visible()
    product_page.go_to_checkout()

    checkout = CheckoutPage(page)
    checkout.fill(EMAIL, SHIPPING)
    checkout.submit()

    expect(page).to_have_url(URL_PATTERN)
    order = OrderPage(page)
    expect(order.status("Oczekuje na płatność")).to_be_visible()
    expect(order.total).to_have_text(f"{product.price},00 zł")

    # Płatność potwierdza powiadomienie przez API, takie jak wysyła operator płatności.
    paid = shop.notify(order_id_by_token(db, order.token), "COMPLETED")
    assert paid.status_code == 200, paid.text
    page.reload()
    expect(order.status("Opłacone")).to_be_visible()
