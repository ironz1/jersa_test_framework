from collections.abc import Callable

import pytest

from jersa.schemas.loader import SCHEMAS_DIR, SchemaRegistry


@pytest.fixture(scope="session")
def schema_registry() -> SchemaRegistry:
    """Schematy wczytane raz na sesję."""
    return SchemaRegistry(SCHEMAS_DIR)


@pytest.fixture
def assert_matches_schema(schema_registry: SchemaRegistry) -> Callable[[object, str], None]:
    """`assert_matches_schema(body, "search")` kończy test listą niezgodności, każda w linii."""

    def _assert(instance: object, name: str) -> None:
        errors = schema_registry.errors(instance, name)
        if errors:
            pytest.fail(f"Odpowiedź niezgodna ze schematem '{name}':\n" + "\n".join(errors))

    return _assert
