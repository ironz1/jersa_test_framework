import pytest
from playwright.sync_api import expect

from jersa.clients.commerce import BUYER, EMAIL
from jersa.pages.cart_page import CartPage
from jersa.pages.checkout_page import COURIER, COURIER_PRICE, CheckoutPage
from jersa.pages.order_page import URL_PATTERN, OrderPage
from jersa.pages.product_page import ProductPage


@pytest.mark.regression
def test_guest_buys_with_discount_code(page, make_product, make_discount_code):
    """E-04: gość stosuje kod rabatowy w koszyku i płaci w kasie sumę z rabatem i dostawą."""
    own = make_product(amount=200)
    code = make_discount_code(kind="percent", value=10)

    product_page = ProductPage(page)
    product_page.open(own.slug)
    product_page.choose_size("36")
    product_page.add_to_cart()
    expect(product_page.cart_drawer).to_be_visible()

    cart = CartPage(page)
    cart.open()
    cart.apply_code(code.code)
    expect(cart.discount(code.code)).to_be_visible()
    cart.go_to_checkout()

    checkout = CheckoutPage(page)
    checkout.fill(EMAIL, BUYER)
    checkout.choose_delivery(COURIER)
    checkout.accept_terms()
    checkout.submit()

    expect(page).to_have_url(URL_PATTERN)
    expect(OrderPage(page).total).to_have_text(f"{200 - 20 + COURIER_PRICE},00 zł")
