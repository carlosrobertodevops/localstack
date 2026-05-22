"""GCP integration with the existing cloud/edge.MultiCloudEdge dispatcher."""

import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.cloud import CloudRegistry, MultiCloudEdge, register_builtins


@pytest.fixture
def registry():
    r = CloudRegistry()
    register_builtins(r)
    return r


@pytest.fixture
def client(registry):
    return Client(MultiCloudEdge(registry=registry), Response)


def test_gcp_storage_routes_via_edge(client):
    r = client.post(
        "/storage/v1/b?project=p1",
        data=json.dumps({"name": "edge-bucket"}),
        content_type="application/json",
        headers={"Host": "storage.googleapis.com"},
    )
    assert r.status_code == 200


def test_gcp_pubsub_routes_via_edge(client):
    r = client.put(
        "/v1/projects/p1/topics/t1",
        headers={"Host": "pubsub.googleapis.com"},
    )
    assert r.status_code == 200


def test_gcp_oauth2_routes_via_edge(client):
    r = client.post(
        "/token",
        data={"grant_type": "client_credentials"},
        headers={"Host": "oauth2.googleapis.com"},
    )
    assert r.status_code == 200


def test_azure_and_gcp_coexist(client):
    # Azure blob via Azure cloud
    r1 = client.put(
        "/c1?restype=container",
        headers={"Host": "acct1.blob.core.windows.net"},
    )
    assert r1.status_code == 201
    # GCS bucket via GCP cloud
    r2 = client.post(
        "/storage/v1/b?project=p1",
        data=json.dumps({"name": "both-clouds"}),
        content_type="application/json",
        headers={"Host": "storage.googleapis.com"},
    )
    assert r2.status_code == 200


def test_gcp_registered_in_registry(registry):
    assert "gcp" in registry.list()
    gcp = registry.get("gcp")
    assert gcp.display_name == "Google Cloud Platform"
    assert "storage.googleapis.com" in gcp.edge_hosts


# ---- Tier-2 edge routing ----------------------------------------------------


def test_bigquery_routes_via_edge(client):
    r = client.post(
        "/bigquery/v2/projects/p1/datasets",
        data=json.dumps({"datasetReference": {"datasetId": "ds1", "projectId": "p1"}}),
        content_type="application/json",
        headers={"Host": "bigquery.googleapis.com"},
    )
    assert r.status_code == 200


def test_secretmanager_routes_via_edge(client):
    r = client.post(
        "/v1/projects/p1/secrets?secretId=s1",
        data=b"{}",
        content_type="application/json",
        headers={"Host": "secretmanager.googleapis.com"},
    )
    assert r.status_code == 200


def test_kms_routes_via_edge(client):
    r = client.post(
        "/v1/projects/p1/locations/us-central1/keyRings?keyRingId=kr1",
        data=b"{}",
        content_type="application/json",
        headers={"Host": "cloudkms.googleapis.com"},
    )
    assert r.status_code == 200


def test_cloudtasks_routes_via_edge(client):
    r = client.post(
        "/v2/projects/p1/locations/us-central1/queues?queueId=q1",
        data=b"{}",
        content_type="application/json",
        headers={"Host": "cloudtasks.googleapis.com"},
    )
    assert r.status_code == 200


def test_cloudrun_routes_via_edge(client):
    r = client.post(
        "/v2/projects/p1/locations/us-central1/services?serviceId=svc1",
        data=json.dumps({"template": {"containers": [{"image": "img:1", "env": []}]}}),
        content_type="application/json",
        headers={"Host": "run.googleapis.com"},
    )
    assert r.status_code == 200


def test_logging_routes_via_edge(client):
    r = client.post(
        "/v2/entries:write",
        data=json.dumps(
            {"entries": [{"logName": "projects/p1/logs/app", "severity": "INFO", "textPayload": "hi"}]}
        ),
        content_type="application/json",
        headers={"Host": "logging.googleapis.com"},
    )
    assert r.status_code == 200


# ---- Tier-3 edge routing ----------------------------------------------------


def test_cloudsql_routes_via_edge(client):
    r = client.post(
        "/sql/v1beta4/projects/p1/instances",
        data=json.dumps(
            {"name": "i1", "region": "us-central1", "databaseVersion": "MYSQL_8_0", "settings": {"tier": "db-n1-standard-1"}}
        ),
        content_type="application/json",
        headers={"Host": "sqladmin.googleapis.com"},
    )
    assert r.status_code == 200


def test_scheduler_routes_via_edge(client):
    r = client.post(
        "/v1/projects/p1/locations/us-central1/jobs",
        data=json.dumps(
            {
                "name": "projects/p1/locations/us-central1/jobs/j1",
                "schedule": "*/5 * * * *",
                "httpTarget": {"uri": "https://x"},
            }
        ),
        content_type="application/json",
        headers={"Host": "cloudscheduler.googleapis.com"},
    )
    assert r.status_code == 200


def test_dns_routes_via_edge(client):
    r = client.post(
        "/dns/v1/projects/p1/managedZones",
        data=json.dumps({"name": "z1", "dnsName": "example.com."}),
        content_type="application/json",
        headers={"Host": "dns.googleapis.com"},
    )
    assert r.status_code == 200


def test_spanner_routes_via_edge(client):
    r = client.post(
        "/v1/projects/p1/instances",
        data=json.dumps(
            {
                "instanceId": "i1",
                "instance": {"config": "projects/_/instanceConfigs/regional-us-central1", "nodeCount": 1},
            }
        ),
        content_type="application/json",
        headers={"Host": "spanner.googleapis.com"},
    )
    assert r.status_code == 200


def test_memorystore_routes_via_edge(client):
    r = client.post(
        "/v1/projects/p1/locations/us-central1/instances?instanceId=i1",
        data=json.dumps({"tier": "BASIC", "memorySizeGb": 1}),
        content_type="application/json",
        headers={"Host": "redis.googleapis.com"},
    )
    assert r.status_code == 200


def test_all_tier2_tier3_hosts_registered(registry):
    gcp = registry.get("gcp")
    expected = {
        "bigquery.googleapis.com",
        "secretmanager.googleapis.com",
        "cloudkms.googleapis.com",
        "cloudtasks.googleapis.com",
        "run.googleapis.com",
        "logging.googleapis.com",
        "sqladmin.googleapis.com",
        "cloudscheduler.googleapis.com",
        "dns.googleapis.com",
        "spanner.googleapis.com",
        "redis.googleapis.com",
    }
    assert expected.issubset(set(gcp.edge_hosts))
