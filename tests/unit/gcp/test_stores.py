from localstack.gcp.stores import CaseInsensitiveDict, GcpProject, GcpStores


def test_case_insensitive_dict_set_get():
    d = CaseInsensitiveDict()
    d["Foo"] = 1
    assert d["foo"] == 1
    assert "FOO" in d


def test_case_insensitive_dict_delete_pop():
    d = CaseInsensitiveDict()
    d["X"] = 9
    assert d.pop("x") == 9
    d["X"] = 7
    del d["x"]
    assert "x" not in d


def test_gcp_stores_lazy_creation():
    s = GcpStores()
    assert not s.has_project("p1")
    store = s.get_project("p1")
    assert store.project is None
    assert s.has_project("p1")


def test_gcp_stores_case_insensitive():
    s = GcpStores()
    s.get_project("P1").project = GcpProject(project_id="P1")
    assert s.has_project("p1")
    assert s.get_project("p1").project.project_id == "P1"


def test_gcp_stores_clear():
    s = GcpStores()
    s.get_project("p1")
    s.clear()
    assert not s.has_project("p1")
