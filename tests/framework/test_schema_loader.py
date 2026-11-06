import json

import pytest

from jersa.schemas.loader import SchemaRegistry


@pytest.fixture
def schemas_dir(tmp_path):
    item = {
        "$id": "item.json",
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
        "additionalProperties": False,
    }
    listing = {
        "$id": "list.json",
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"$ref": "item.json"}}},
        "additionalProperties": False,
    }
    (tmp_path / "item.json").write_text(json.dumps(item), encoding="utf-8")
    (tmp_path / "list.json").write_text(json.dumps(listing), encoding="utf-8")
    return tmp_path


def test_valid_instance_has_no_errors(schemas_dir):
    assert SchemaRegistry(schemas_dir).errors({"items": [{"name": "a"}]}, "list") == []


def test_extra_property_reported_with_path(schemas_dir):
    errors = SchemaRegistry(schemas_dir).errors({"items": [{"name": "a", "x": 1}]}, "list")
    assert len(errors) == 1
    assert errors[0].startswith("$.items[0]: ")
    assert "'x' was unexpected" in errors[0]


def test_missing_required_property_reported(schemas_dir):
    errors = SchemaRegistry(schemas_dir).errors({"items": [{}]}, "list")
    assert errors == ["$.items[0]: 'name' is a required property"]


def test_wrong_type_reported(schemas_dir):
    errors = SchemaRegistry(schemas_dir).errors({"items": [{"name": 1}]}, "list")
    assert errors == ["$.items[0].name: 1 is not of type 'string'"]


def test_unknown_schema_name_lists_available(schemas_dir):
    with pytest.raises(FileNotFoundError, match=r"nope.*item, list"):
        SchemaRegistry(schemas_dir).errors({}, "nope")
