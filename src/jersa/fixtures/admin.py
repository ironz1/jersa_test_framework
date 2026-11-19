from collections.abc import Iterator

import psycopg
import pytest
from playwright.sync_api import Browser

from jersa.clients.admin import ADMIN_COOKIE, AdminApi
from jersa.clients.api_client import ApiClient
from jersa.config import Settings
from jersa.db.discount_codes import code_ids, delete_discount_code


@pytest.fixture(scope="session")
def admin_cookie(browser: Browser, base_url: str, settings: Settings) -> str:
    """Logowanie do panelu przez formularz `/admin/login`, raz na proces testów.

    Panel loguje akcją serwera Next.js, więc zwykłe żądanie HTTP nie wystarczy. Przeglądarka
    wypełnia formularz tak jak operator, a test API dostaje wartość ciasteczka sesji panelu."""
    context = browser.new_context(base_url=base_url)
    try:
        page = context.new_page()
        page.goto("/admin/login")
        page.get_by_label("Hasło").fill(settings.admin_password.get_secret_value())
        page.get_by_role("button", name="Wejdź").click()
        # Sukces przekierowuje na /admin, złe hasło na /admin/login?blad=1.
        page.wait_for_url(lambda url: "/admin/login" not in url or "blad=" in url)
        cookie = next((c for c in context.cookies() if c["name"] == ADMIN_COOKIE), None)
        if cookie is None:
            raise RuntimeError("Logowanie do panelu nie ustawiło ciasteczka: złe ADMIN_PASSWORD?")
        return cookie["value"]
    finally:
        context.close()


@pytest.fixture
def admin(db: psycopg.Connection, base_url: str, admin_cookie: str) -> Iterator[AdminApi]:
    """Zalogowany klient panelu. Po teście, także nieudanym, kody, o które prosił, znikają
    z bazy po ID (tylko kody z prefiksem `test-`). Zależy od `db`: bez DATABASE_URL pomijany."""
    client = ApiClient(base_url)
    client.cookies.set(ADMIN_COOKIE, admin_cookie)
    api = AdminApi(client)
    yield api
    client.close()
    for code in api.created_codes:
        for code_id in code_ids(db, code):
            delete_discount_code(db, code_id)


@pytest.fixture
def anonymous_admin(api_client: ApiClient) -> AdminApi:
    """Klient panelu bez logowania."""
    return AdminApi(api_client)
