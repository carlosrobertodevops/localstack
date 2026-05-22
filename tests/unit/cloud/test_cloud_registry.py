import pytest

from localstack.cloud import CloudProvider, CloudRegistry


def _stub_factory(name="stub"):
    return lambda: f"gw-{name}"


def test_register_and_get():
    reg = CloudRegistry()
    p = CloudProvider(
        name="aws",
        display_name="Amazon Web Services",
        package="localstack.aws",
        gateway_factory=_stub_factory("aws"),
    )
    reg.register(p)
    assert reg.get("aws") is p
    assert reg.get("AWS") is p  # case-insensitive
    assert "aws" in reg
    assert len(reg) == 1


def test_register_duplicate_raises_unless_replace():
    reg = CloudRegistry()
    a = CloudProvider("x", "X", "p.x", _stub_factory("1"))
    b = CloudProvider("x", "X2", "p.x", _stub_factory("2"))
    reg.register(a)
    with pytest.raises(ValueError):
        reg.register(b)
    reg.register(b, replace=True)
    assert reg.get("x").display_name == "X2"


def test_list_returns_sorted_names():
    reg = CloudRegistry()
    reg.register(CloudProvider("zeta", "Z", "p.z", _stub_factory("z")))
    reg.register(CloudProvider("alpha", "A", "p.a", _stub_factory("a")))
    assert reg.list() == ("alpha", "zeta")


def test_iter_yields_providers_in_sorted_order():
    reg = CloudRegistry()
    reg.register(CloudProvider("b", "B", "p.b", _stub_factory("b")))
    reg.register(CloudProvider("a", "A", "p.a", _stub_factory("a")))
    assert [p.name for p in reg] == ["a", "b"]


def test_require_missing_raises():
    reg = CloudRegistry()
    with pytest.raises(LookupError):
        reg.require("nope")


def test_unregister():
    reg = CloudRegistry()
    reg.register(CloudProvider("x", "X", "p.x", _stub_factory("x")))
    reg.unregister("X")
    assert reg.get("x") is None


def test_build_gateway_invokes_factory():
    reg = CloudRegistry()
    reg.register(CloudProvider("aws", "AWS", "p.aws", _stub_factory("aws")))
    assert reg.get("aws").build_gateway() == "gw-aws"


def test_provider_with_optional_factories():
    p = CloudProvider("x", "X", "p.x", _stub_factory("x"))
    assert p.build_state_store() is None
    assert p.build_plugin_registry() is None
