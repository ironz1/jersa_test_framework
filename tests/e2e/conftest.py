import pytest

from jersa.db.sessions import CART_COOKIE, WISH_COOKIE, cleanup_sessions


@pytest.fixture(autouse=True)
def _clean_browser_session(context, settings):
    """Po każdym teście E2E usuwa z bazy koszyk i przechowalnię, które utworzyła przeglądarka.
    Bez DATABASE_URL (np. STG) nic nie robi."""
    yield
    cookies = {cookie["name"]: cookie["value"] for cookie in context.cookies()}
    cleanup_sessions(settings.database_url, [(cookies.get(CART_COOKIE), cookies.get(WISH_COOKIE))])
