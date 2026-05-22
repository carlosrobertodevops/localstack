import json

import pytest

from localstack.gcp.exceptions import GcpNotFound
from localstack.gcp.serializers import (
    make_operation_name,
    parse_json_body,
    serialize_error,
    serialize_operation,
)


def test_serialize_error_shape():
    status, body = serialize_error(GcpNotFound("missing thing"))
    assert status == 404
    parsed = json.loads(body)
    assert parsed["error"]["code"] == 404
    assert parsed["error"]["status"] == "ResourceNotFound"
    assert parsed["error"]["message"] == "missing thing"


def test_parse_json_body_empty():
    assert parse_json_body(None) == {}
    assert parse_json_body(b"") == {}
    assert parse_json_body("") == {}


def test_parse_json_body_invalid():
    with pytest.raises(ValueError):
        parse_json_body(b"not-json")


def test_parse_json_body_array_rejected():
    with pytest.raises(ValueError):
        parse_json_body(b"[1,2]")


def test_operation_envelope():
    op = serialize_operation("op-1", done=True, response={"x": 1})
    assert op["name"] == "op-1"
    assert op["done"] is True
    assert op["response"] == {"x": 1}


def test_operation_name_format():
    name = make_operation_name("storage", "my-proj")
    assert name.startswith("projects/my-proj/locations/global/operations/storage-")
