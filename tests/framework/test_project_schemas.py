import json

import pytest
from jsonschema import Draft202012Validator

from jersa.schemas.loader import SCHEMAS_DIR

SCHEMA_FILES = sorted(SCHEMAS_DIR.glob("*.json"))


def _open_objects(node: object, path: str = "$") -> list[str]:
    """Ścieżki obiektów z `properties`, które nie mają `additionalProperties: false`."""
    found: list[str] = []
    if isinstance(node, dict):
        if "properties" in node and node.get("additionalProperties") is not False:
            found.append(path)
        for key, value in node.items():
            found += _open_objects(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found += _open_objects(value, f"{path}[{index}]")
    return found


def test_schemas_directory_is_not_empty():
    assert SCHEMA_FILES, f"Brak schematów w {SCHEMAS_DIR}"


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda path: path.name)
def test_schema_is_valid_and_closed(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == path.name
    assert _open_objects(schema) == []
