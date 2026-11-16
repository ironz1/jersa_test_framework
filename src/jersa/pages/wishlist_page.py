"""Przechowalnia (ulubione): `/ulubione`."""

import re

from playwright.sync_api import Locator, Page


class WishlistPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def open(self) -> None:
        self._page.goto("/ulubione")

    @property
    def heading(self) -> Locator:
        return self._page.get_by_role("heading", name=re.compile("Ulubione", re.IGNORECASE))

    def item(self, name: str) -> Locator:
        return self._page.get_by_role("link", name=re.compile(re.escape(name)))
