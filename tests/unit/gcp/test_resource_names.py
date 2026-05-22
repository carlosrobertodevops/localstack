import pytest

from localstack.gcp.exceptions import GcpInvalidResourceName
from localstack.gcp.resource_names import GcpResourceName


def test_parse_with_location():
    name = GcpResourceName.parse("projects/p1/locations/us-central1/functions/myfn")
    assert name.project == "p1"
    assert name.location == "us-central1"
    assert name.resource_type == "functions"
    assert name.name == "myfn"
    assert name.child_resources == ()


def test_parse_without_location():
    name = GcpResourceName.parse("projects/p1/buckets/my-bucket")
    assert name.project == "p1"
    assert name.location is None
    assert name.resource_type == "buckets"
    assert name.name == "my-bucket"


def test_parse_with_even_children():
    name = GcpResourceName.parse(
        "projects/p1/databases/(default)/documents/users"
    )
    assert name.resource_type == "databases"
    assert name.name == "(default)"
    assert name.child_resources == (("documents", "users"),)


def test_parse_invalid_missing_projects():
    with pytest.raises(GcpInvalidResourceName):
        GcpResourceName.parse("foo/bar/baz")


def test_parse_invalid_odd_children():
    with pytest.raises(GcpInvalidResourceName):
        GcpResourceName.parse("projects/p1/locations/us/functions/f1/extra")


def test_full_name_roundtrip():
    raw = "projects/p1/locations/us-central1/functions/myfn"
    n = GcpResourceName.parse(raw)
    assert n.full_name == raw


def test_full_name_without_location():
    n = GcpResourceName(project="p1", location=None, resource_type="buckets", name="b1")
    assert n.full_name == "projects/p1/buckets/b1"
