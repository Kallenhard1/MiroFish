from app.db.bootstrap import recover_orphaned_tasks
from app.models.task import TaskManager, TaskStatus


def test_recover_marks_processing_as_failed():
    tm = TaskManager()
    tid = tm.create_task("report_generate", {"report_id": "r1"})
    tm.update_task(tid, status=TaskStatus.PROCESSING, progress=40)

    count = recover_orphaned_tasks()

    assert count == 1
    task = tm.get_task(tid)
    assert task.status == TaskStatus.FAILED
    assert "restart" in (task.error or "").lower()


def test_recover_leaves_completed_untouched():
    tm = TaskManager()
    done = tm.create_task("graph_build", {})
    tm.complete_task(done, result={"graph_id": "g1"})

    recover_orphaned_tasks()

    assert tm.get_task(done).status == TaskStatus.COMPLETED


def test_recover_marks_pending_as_failed():
    tm = TaskManager()
    pending = tm.create_task("graph_build", {})  # never started

    count = recover_orphaned_tasks()

    assert count == 1
    assert tm.get_task(pending).status == TaskStatus.FAILED
