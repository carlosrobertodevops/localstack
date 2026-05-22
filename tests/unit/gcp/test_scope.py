from localstack.gcp.scope import GcpScope


def test_for_project():
    s = GcpScope.for_project("p1")
    assert s.project_id == "p1"
    assert s.location is None


def test_for_location():
    s = GcpScope.for_location("p1", "us-central1")
    assert s.project_id == "p1"
    assert s.location == "us-central1"


def test_from_resource_name():
    s = GcpScope.from_resource_name("projects/p1/locations/us-east1/functions/x")
    assert s.project_id == "p1"
    assert s.location == "us-east1"


def test_from_resource_name_without_location():
    s = GcpScope.from_resource_name("projects/p1/buckets/b1")
    assert s.project_id == "p1"
    assert s.location is None
