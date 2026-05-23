import pytest

from localstack.gcp.defaults import create_default_registry
from localstack.gcp.exceptions import GcpUnsupportedOperation
from localstack.gcp.spec import GcpServiceSpec, GcpServiceSpecRegistry


def test_register_get():
    r = GcpServiceSpecRegistry()
    r.register(GcpServiceSpec("storage", "buckets", ("v1",)))
    spec = r.get("storage", "buckets")
    assert spec.service == "storage"


def test_register_validates():
    r = GcpServiceSpecRegistry()
    with pytest.raises(ValueError):
        r.register(GcpServiceSpec("", "buckets", ("v1",)))
    with pytest.raises(ValueError):
        r.register(GcpServiceSpec("storage", "", ("v1",)))
    with pytest.raises(ValueError):
        r.register(GcpServiceSpec("storage", "buckets", ()))


def test_unknown_raises():
    r = GcpServiceSpecRegistry()
    with pytest.raises(GcpUnsupportedOperation):
        r.get("nope", "x")


def test_default_registry_has_tier1():
    r = create_default_registry()
    services = set(r.services())
    assert {"storage", "pubsub", "firestore", "cloudfunctions", "iam"} <= services


def test_default_registry_locations():
    r = create_default_registry()
    spec = r.get("storage", "buckets")
    assert "us-central1" in spec.locations
