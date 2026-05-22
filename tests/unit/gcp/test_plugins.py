from localstack.gcp.plugins import GcpProviderPlugin, GcpProviderRegistry, iter_builtin_plugins


def test_register_and_get():
    r = GcpProviderRegistry()
    r.register(GcpProviderPlugin("storage", "buckets", lambda: None))
    plugin = r.get("STORAGE", "Buckets")
    assert plugin is not None
    assert plugin.name == "storage/buckets"


def test_missing_returns_none():
    r = GcpProviderRegistry()
    assert r.get("none", "x") is None


def test_load_builtins_covers_tier1():
    r = GcpProviderRegistry()
    r.load_builtins()
    services = set(r.services())
    assert {"storage", "pubsub", "firestore", "cloudfunctions", "iam"} <= services


def test_iter_builtin_plugins_unique():
    seen = set()
    for p in iter_builtin_plugins():
        key = (p.service, p.resource_type)
        assert key not in seen
        seen.add(key)
    assert len(seen) >= 5
