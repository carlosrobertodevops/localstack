from pathlib import Path

import pytest

from localstack.gcp.gateway import GcpGateway
from localstack.gcp.state import GcpStateStore


def test_snapshot_restore_buckets(tmp_path: Path):
    g = GcpGateway()
    g.storage_provider.create_bucket(project="p1", name="b1")
    g.storage_provider.put_object("b1", "k1", b"hello")

    snap = tmp_path / "snap.pkl"
    GcpStateStore().snapshot(g, snap)

    g2 = GcpGateway()
    assert "b1" not in g2.storage_provider.data.buckets
    GcpStateStore().restore(g2, snap)
    assert "b1" in g2.storage_provider.data.buckets
    assert g2.storage_provider.get_object("b1", "k1").content == b"hello"


def test_restore_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        GcpStateStore().restore(GcpGateway(), tmp_path / "nope.pkl")


def test_snapshot_restore_pubsub(tmp_path: Path):
    g = GcpGateway()
    g.pubsub_provider.create_topic("projects/p1/topics/t1")
    g.pubsub_provider.create_subscription(
        "projects/p1/subscriptions/s1", "projects/p1/topics/t1"
    )
    snap = tmp_path / "snap.pkl"
    GcpStateStore().snapshot(g, snap)

    g2 = GcpGateway()
    GcpStateStore().restore(g2, snap)
    assert "projects/p1/topics/t1" in g2.pubsub_provider.data.topics
    assert "projects/p1/subscriptions/s1" in g2.pubsub_provider.data.subscriptions
