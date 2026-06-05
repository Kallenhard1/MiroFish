from app.models.task import TaskManager, TaskStatus


def test_create_and_get_returns_task_object():
    tm = TaskManager()
    tid = tm.create_task("report_generate", {"report_id": "r1"})
    task = tm.get_task(tid)
    assert task is not None
    assert task.task_type == "report_generate"
    assert task.status == TaskStatus.PENDING
    assert task.metadata == {"report_id": "r1"}


def test_get_missing_returns_none():
    assert TaskManager().get_task("missing") is None


def test_update_task_persists():
    tm = TaskManager()
    tid = tm.create_task("graph_build", {})
    tm.update_task(tid, status=TaskStatus.PROCESSING, progress=30, message="go")
    task = tm.get_task(tid)
    assert task.status == TaskStatus.PROCESSING
    assert task.progress == 30
    assert task.message == "go"


def test_complete_task():
    tm = TaskManager()
    tid = tm.create_task("graph_build", {})
    tm.complete_task(tid, result={"graph_id": "g9"})
    task = tm.get_task(tid)
    assert task.status == TaskStatus.COMPLETED
    assert task.progress == 100
    assert task.result == {"graph_id": "g9"}


def test_fail_task():
    tm = TaskManager()
    tid = tm.create_task("graph_build", {})
    tm.fail_task(tid, "boom")
    task = tm.get_task(tid)
    assert task.status == TaskStatus.FAILED
    assert task.error == "boom"


def test_to_dict_shape_preserved():
    tm = TaskManager()
    tid = tm.create_task("graph_build", {"project_id": "p1"})
    d = tm.get_task(tid).to_dict()
    assert d["task_id"] == tid
    assert d["status"] == "pending"
    assert d["metadata"] == {"project_id": "p1"}


def test_cancel_passthrough():
    tm = TaskManager()
    tid = tm.create_task("report_generate", {})
    assert tm.is_cancel_requested(tid) is False
    tm.request_cancel(tid)
    assert tm.is_cancel_requested(tid) is True


def test_survives_new_manager_instance():
    # Durability: a different TaskManager instance still sees the task (it's in the DB).
    tid = TaskManager().create_task("graph_build", {})
    assert TaskManager().get_task(tid) is not None
