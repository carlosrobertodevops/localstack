import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.logging import LoggingProvider, LoggingRouter


@pytest.fixture
def client():
    return Client(LoggingRouter(provider=LoggingProvider()), Response)


def _write(client, entries):
    return client.post(
        "/v2/entries:write",
        data=json.dumps({"entries": entries}),
        content_type="application/json",
    )


def _list(client, project="p1", filter_expr="", page_size=50):
    return client.post(
        "/v2/entries:list",
        data=json.dumps(
            {"projectIds": [project], "filter": filter_expr, "pageSize": page_size}
        ),
        content_type="application/json",
    )


def test_write_entries(client):
    r = _write(
        client,
        [
            {
                "logName": "projects/p1/logs/app",
                "severity": "INFO",
                "textPayload": "hello",
            }
        ],
    )
    assert r.status_code == 200
    assert json.loads(r.data)["entriesWritten"] == 1


def test_list_returns_entries(client):
    _write(client, [{"logName": "projects/p1/logs/app", "severity": "INFO", "textPayload": "x"}])
    r = _list(client)
    entries = json.loads(r.data)["entries"]
    assert len(entries) == 1
    assert entries[0]["textPayload"] == "x"


def test_filter_severity_gte_error(client):
    _write(
        client,
        [
            {"logName": "projects/p1/logs/app", "severity": "INFO", "textPayload": "a"},
            {"logName": "projects/p1/logs/app", "severity": "ERROR", "textPayload": "b"},
            {"logName": "projects/p1/logs/app", "severity": "CRITICAL", "textPayload": "c"},
        ],
    )
    r = _list(client, filter_expr="severity>=ERROR")
    entries = json.loads(r.data)["entries"]
    assert {e["textPayload"] for e in entries} == {"b", "c"}


def test_filter_by_log_name(client):
    _write(
        client,
        [
            {"logName": "projects/p1/logs/app", "severity": "INFO", "textPayload": "a"},
            {"logName": "projects/p1/logs/sys", "severity": "INFO", "textPayload": "b"},
        ],
    )
    r = _list(client, filter_expr='logName="projects/p1/logs/app"')
    entries = json.loads(r.data)["entries"]
    assert [e["textPayload"] for e in entries] == ["a"]


def test_filter_compound(client):
    _write(
        client,
        [
            {"logName": "projects/p1/logs/app", "severity": "INFO", "textPayload": "a"},
            {"logName": "projects/p1/logs/app", "severity": "ERROR", "textPayload": "b"},
            {"logName": "projects/p1/logs/sys", "severity": "ERROR", "textPayload": "c"},
        ],
    )
    r = _list(
        client,
        filter_expr='logName="projects/p1/logs/app" AND severity>=ERROR',
    )
    entries = json.loads(r.data)["entries"]
    assert [e["textPayload"] for e in entries] == ["b"]


def test_delete_log_clears_matching(client):
    _write(
        client,
        [
            {"logName": "projects/p1/logs/app", "severity": "INFO", "textPayload": "a"},
            {"logName": "projects/p1/logs/sys", "severity": "INFO", "textPayload": "b"},
        ],
    )
    r = client.delete("/v2/projects/p1/logs/app")
    assert r.status_code == 200
    r = _list(client)
    entries = json.loads(r.data)["entries"]
    assert [e["textPayload"] for e in entries] == ["b"]


def test_create_sink(client):
    r = client.post(
        "/v2/projects/p1/sinks",
        data=json.dumps(
            {
                "name": "projects/p1/sinks/sink1",
                "destination": "storage.googleapis.com/bucket",
                "filter": "severity>=ERROR",
            }
        ),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert json.loads(r.data)["name"].endswith("/sinks/sink1")


def test_duplicate_sink(client):
    body = json.dumps({"name": "projects/p1/sinks/sink1", "destination": "x"})
    client.post("/v2/projects/p1/sinks", data=body, content_type="application/json")
    r = client.post("/v2/projects/p1/sinks", data=body, content_type="application/json")
    assert r.status_code == 409


def test_get_sink(client):
    client.post(
        "/v2/projects/p1/sinks",
        data=json.dumps({"name": "projects/p1/sinks/s1", "destination": "x"}),
        content_type="application/json",
    )
    r = client.get("/v2/projects/p1/sinks/s1")
    assert r.status_code == 200


def test_list_sinks(client):
    for sid in ("a", "b"):
        client.post(
            "/v2/projects/p1/sinks",
            data=json.dumps({"name": f"projects/p1/sinks/{sid}", "destination": "x"}),
            content_type="application/json",
        )
    r = client.get("/v2/projects/p1/sinks")
    assert len(json.loads(r.data)["sinks"]) == 2


def test_delete_sink(client):
    client.post(
        "/v2/projects/p1/sinks",
        data=json.dumps({"name": "projects/p1/sinks/s1", "destination": "x"}),
        content_type="application/json",
    )
    r = client.delete("/v2/projects/p1/sinks/s1")
    assert r.status_code == 200
    r = client.get("/v2/projects/p1/sinks/s1")
    assert r.status_code == 404


def test_update_sink(client):
    client.post(
        "/v2/projects/p1/sinks",
        data=json.dumps({"name": "projects/p1/sinks/s1", "destination": "x"}),
        content_type="application/json",
    )
    r = client.patch(
        "/v2/projects/p1/sinks/s1",
        data=json.dumps({"destination": "y", "filter": "severity>=ERROR"}),
        content_type="application/json",
    )
    body = json.loads(r.data)
    assert body["destination"] == "y"
    assert body["filter"] == "severity>=ERROR"


def test_entries_cap(client):
    from localstack.gcp.services.logging import models as logging_models

    cap = logging_models.MAX_ENTRIES_PER_PROJECT
    batch = [
        {"logName": "projects/p1/logs/app", "severity": "INFO", "textPayload": str(i)}
        for i in range(cap + 50)
    ]
    _write(client, batch)
    r = _list(client, page_size=cap + 100)
    entries = json.loads(r.data)["entries"]
    assert len(entries) == cap
    assert entries[0]["textPayload"] == "50"
