import pytest

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider


def test_create_project():
    p = ResourceManagerProvider()
    proj = p.create_project("my-proj", name="My Project")
    assert proj.project_id == "my-proj"
    assert proj.state == "ACTIVE"
    assert proj.project_number


def test_create_project_duplicate():
    p = ResourceManagerProvider()
    p.create_project("p1")
    with pytest.raises(GcpAlreadyExists):
        p.create_project("p1")


def test_create_project_requires_id():
    p = ResourceManagerProvider()
    with pytest.raises(GcpInvalidRequest):
        p.create_project("")


def test_get_project_missing():
    p = ResourceManagerProvider()
    with pytest.raises(GcpNotFound):
        p.get_project("nope")


def test_delete_project_marks_state():
    p = ResourceManagerProvider()
    p.create_project("p1")
    p.delete_project("p1")
    assert p.get_project("p1").state == "DELETE_REQUESTED"


def test_ensure_idempotent():
    p = ResourceManagerProvider()
    a = p.ensure_project("p1")
    b = p.ensure_project("p1")
    assert a is b


def test_list_projects():
    p = ResourceManagerProvider()
    p.create_project("p1")
    p.create_project("p2")
    assert {x.project_id for x in p.list_projects()} == {"p1", "p2"}


def test_to_dict_shape():
    p = ResourceManagerProvider()
    proj = p.create_project("p1", name="Display")
    d = p.to_dict(proj)
    assert d["name"] == "projects/p1"
    assert d["projectId"] == "p1"
    assert d["displayName"] == "Display"
    assert d["state"] == "ACTIVE"
