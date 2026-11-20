"""Wzorce nazw produktów dla lokatorów Playwright."""

import re


def name_pattern(name: str) -> re.Pattern[str]:
    """Nazwa dostępna elementu ma spacje zliczone do jednej („SUKIENKA  STELLA” w bazie,
    „SUKIENKA STELLA” w linku), więc każdy odstęp w nazwie pasuje do dowolnego odstępu."""
    return re.compile(r"\s+".join(re.escape(word) for word in name.split()))
