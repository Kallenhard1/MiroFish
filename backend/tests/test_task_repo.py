from app.repositories import task_repo


def test_create_and_get():
    task_repo.create("t1", "report_generate", {"report_id": "r1"})
    row = task_repo.get("t1")
    assert row["task_id"] == "t1"
    assert row["task_type"] == "report_generate"
    assert row["status"] == "pending"
    assert row["progress"] == 0
    assert row["metadata"] == {"report_id": "r1"}
    assert row["cancel_requested"] is False


def test_get_missing_returns_none():
    assert task_repo.get("nope") is None


def test_update_fields():
    task_repo.create("t2", "graph_build", {})
    task_repo.update("t2", status="processing", progress=42, message="working")
    row = task_repo.get("t2")
    assert row["status"] == "processing"
    assert row["progress"] == 42
    assert row["message"] == "working"


def test_update_result_is_json_roundtripped():
    task_repo.create("t3", "graph_build", {})
    task_repo.update("t3", status="completed", result={"graph_id": "g1"})
    row = task_repo.get("t3")
    assert row["result"] == {"graph_id": "g1"}


def test_request_and_check_cancel():
    task_repo.create("t4", "report_generate", {})
    assert task_repo.is_cancel_requested("t4") is False
    task_repo.request_cancel("t4")
    assert task_repo.is_cancel_requested("t4") is True


def test_is_cancel_requested_missing_is_false():
    assert task_repo.is_cancel_requested("ghost") is False


def test_list_filters_by_type():
    task_repo.create("a", "graph_build", {})
    task_repo.create("b", "report_generate", {})
    task_repo.create("c", "graph_build", {})
    all_builds = task_repo.list(task_type="graph_build")
    ids = {t["task_id"] for t in all_builds}
    assert ids == {"a", "c"}


def test_find_processing_for_recovery():
    task_repo.create("p1", "graph_build", {})
    task_repo.update("p1", status="processing")
    task_repo.create("p2", "graph_build", {})
    task_repo.update("p2", status="completed")
    processing = task_repo.find_processing()
    ids = {t["task_id"] for t in processing}
    assert ids == {"p1"}
