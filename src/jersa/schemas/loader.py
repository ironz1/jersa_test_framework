"""Schematy JSON kontraktów API i walidacja z czytelną ścieżką do błędnego pola."""

import json
from collections.abc import Iterable
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from jersa.config import PROJECT_ROOT

SCHEMAS_DIR = PROJECT_ROOT / "schemas"


def _json_path(parts: Iterable[str | int]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


class SchemaRegistry:
    """Wczytuje wszystkie `*.json` z katalogu. Schematy odwołują się do siebie przez
    `"$ref": "<plik>.json"`, a każdy plik ma `"$id": "<plik>.json"`."""

    def __init__(self, schemas_dir: Path) -> None:
        self._schemas: dict[str, dict] = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(schemas_dir.glob("*.json"))
        }
        self._registry = Registry().with_resources(
            (f"{name}.json", Resource.from_contents(schema, default_specification=DRAFT202012))
            for name, schema in self._schemas.items()
        )

    def errors(self, instance: object, name: str) -> list[str]:
        """Lista błędów w formacie `"<ścieżka>: <opis>"`; pusta, gdy instancja jest zgodna."""
        if name not in self._schemas:
            available = ", ".join(sorted(self._schemas))
            raise FileNotFoundError(f"Brak schematu '{name}'. Dostępne: {available}")
        validator = Draft202012Validator(self._schemas[name], registry=self._registry)
        return sorted(
            f"{_json_path(error.absolute_path)}: {error.message}"
            for error in validator.iter_errors(instance)
        )
