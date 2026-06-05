# Persistence Foundation & Task Durability — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the volatile in-memory `TaskManager` with a durable SQLite-backed store, and stand up the SQLite index layer + startup crash-recovery so in-flight builds/reports survive a backend restart.

**Architecture:** Hybrid persistence — files remain authoritative for content; a single SQLite file (`uploads/mirofish.db`) is a queryable index + control plane. Plain stdlib `sqlite3`, one connection per thread, WAL mode + `busy_timeout`. This plan delivers the DB foundation, the full schema (so later plans add code, not migrations), the durable `tasks` store, and crash recovery. Project/simulation/report index seams, the preferences modal, and cancel/manage/usage are follow-on plans.

**Tech Stack:** Python 3.12, Flask, stdlib `sqlite3`, `pytest 8.2.0` (already installed in `backend/.venv`).

**Spec:** `docs/superpowers/specs/2026-06-05-report-persistence-control-design.md`

---

## File Structure

**Create:**
- `backend/app/db/__init__.py` — package marker
- `backend/app/db/connection.py` — `get_conn()` / `close_conn()` (per-thread conn, WAL, pragmas)
- `backend/app/db/schema.sql` — full schema (all tables from the spec)
- `backend/app/db/bootstrap.py` — `init_db()`, `recover_orphaned_tasks()`
- `backend/app/repositories/__init__.py` — package marker
- `backend/app/repositories/task_repo.py` — CRUD + cancel + recovery queries on `tasks`
- `backend/tests/__init__.py` — package marker
- `backend/tests/conftest.py` — pytest fixture pointing `Config.DB_PATH` at a temp DB
- `backend/tests/test_connection.py`
- `backend/tests/test_task_repo.py`
- `backend/tests/test_task_manager.py`
- `backend/tests/test_recovery.py`
- `backend/pytest.ini` — pytest config (test path, rootdir)

**Modify:**
- `backend/app/config.py` — add `DB_PATH`
- `backend/app/models/task.py` — `TaskManager` delegates to `task_repo` (signatures unchanged)
- `backend/app/__init__.py` — call `init_db()` in `create_app()`
- `backend/app/api/graph.py:447` — normalize graph-build `task_type` to `"graph_build"`

All test commands assume the venv python: `backend/.venv/bin/python -m pytest ...`, run from the `backend/` directory.

---

## Task 1: Config + pytest scaffold

**Files:**
- Modify: `backend/app/config.py:38-41`
- Create: `backend/pytest.ini`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Add `DB_PATH` to Config**

In `backend/app/config.py`, under the "File upload configuration" block (after line 41, the `ALLOWED_EXTENSIONS` line), add:

```python
    # SQLite index database (hybrid: files authoritative for content, DB indexes status/tasks)
    DB_PATH = os.path.join(os.path.dirname(__file__), '../uploads/mirofish.db')
```

- [ ] **Step 2: Create pytest config**

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 3: Create tests package marker**

Create `backend/tests/__init__.py` (empty file):

```python
```

- [ ] **Step 4: Create conftest with an isolated temp DB fixture**

Create `backend/tests/conftest.py`:

```python
import os
import tempfile
import pytest

from app.config import Config
from app.db import connection as conn_mod


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """Point Config.DB_PATH at a fresh temp file and reset the per-thread
    connection for every test, so tests never touch the real uploads/ DB."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(Config, "DB_PATH", path)
    conn_mod.close_conn()  # drop any cached connection from a previous test

    # create schema in the temp db
    from app.db.bootstrap import _apply_schema
    _apply_schema()

    yield path

    conn_mod.close_conn()
    if os.path.exists(path):
        os.remove(path)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/pytest.ini backend/tests/__init__.py backend/tests/conftest.py
git commit -m "chore(db): add DB_PATH config and pytest scaffold"
```

---

## Task 2: Connection helper

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/connection.py`
- Test: `backend/tests/test_connection.py`

- [ ] **Step 1: Create db package marker**

Create `backend/app/db/__init__.py` (empty file):

```python
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_connection.py`:

```python
from app.db.connection import get_conn, close_conn


def test_get_conn_returns_same_conn_within_thread():
    c1 = get_conn()
    c2 = get_conn()
    assert c1 is c2


def test_wal_mode_enabled():
    conn = get_conn()
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert mode.lower() == "wal"


def test_foreign_keys_enabled():
    conn = get_conn()
    fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk == 1


def test_close_conn_forces_new_connection():
    c1 = get_conn()
    close_conn()
    c2 = get_conn()
    assert c1 is not c2


def test_row_factory_returns_mapping():
    conn = get_conn()
    row = conn.execute("SELECT 1 AS one;").fetchone()
    assert row["one"] == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_connection.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.db.connection'`)

- [ ] **Step 4: Implement the connection helper**

Create `backend/app/db/connection.py`:

```python
"""Per-thread SQLite connection helper.

Python's sqlite3 forbids sharing a connection across threads, and the backend
spawns a daemon thread per build/report. So each thread lazily opens its own
connection. WAL mode allows many readers + one writer; busy_timeout makes the
writer wait instead of raising 'database is locked'.
"""

import sqlite3
import threading

from ..config import Config

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(Config.DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        _local.conn = conn
    return conn


def close_conn() -> None:
    """Close and forget this thread's connection (used in tests/teardown)."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_connection.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/__init__.py backend/app/db/connection.py backend/tests/test_connection.py
git commit -m "feat(db): per-thread sqlite connection helper with WAL + pragmas"
```

---

## Task 3: Schema + bootstrap (`_apply_schema` / `init_db`)

**Files:**
- Create: `backend/app/db/schema.sql`
- Create: `backend/app/db/bootstrap.py`
- Test: `backend/tests/test_connection.py` (extend with a schema test)

> Note: `conftest.py` (Task 1) already imports `_apply_schema`; this task creates it. Until this task lands, other tests fail to set up — implement Tasks 1→2→3 in order.

- [ ] **Step 1: Create the schema file**

Create `backend/app/db/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS projects (
  project_id            TEXT PRIMARY KEY,
  name                  TEXT NOT NULL,
  status                TEXT NOT NULL,
  graph_id              TEXT,
  graph_build_task_id   TEXT,
  simulation_requirement TEXT,
  chunk_size            INTEGER DEFAULT 500,
  chunk_overlap         INTEGER DEFAULT 50,
  limits                TEXT,
  report_preferences    TEXT,
  total_text_length     INTEGER DEFAULT 0,
  archived              INTEGER DEFAULT 0,
  error                 TEXT,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulations (
  simulation_id   TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  graph_id        TEXT,
  status          TEXT NOT NULL,
  enable_twitter  INTEGER DEFAULT 1,
  enable_reddit   INTEGER DEFAULT 1,
  entities_count  INTEGER DEFAULT 0,
  profiles_count  INTEGER DEFAULT 0,
  current_round   INTEGER DEFAULT 0,
  total_rounds    INTEGER DEFAULT 0,
  config_generated INTEGER DEFAULT 0,
  error           TEXT,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
  report_id              TEXT PRIMARY KEY,
  simulation_id          TEXT REFERENCES simulations(simulation_id) ON DELETE CASCADE,
  project_id             TEXT REFERENCES projects(project_id) ON DELETE CASCADE,
  graph_id               TEXT,
  status                 TEXT NOT NULL,
  title                  TEXT,
  summary                TEXT,
  simulation_requirement TEXT,
  preferences            TEXT,
  usage                  TEXT,
  error                  TEXT,
  created_at             TEXT NOT NULL,
  completed_at           TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id          TEXT PRIMARY KEY,
  task_type        TEXT NOT NULL,
  status           TEXT NOT NULL,
  progress         INTEGER DEFAULT 0,
  message          TEXT,
  result           TEXT,
  error            TEXT,
  metadata         TEXT,
  cancel_requested INTEGER DEFAULT 0,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sims_project    ON simulations(project_id);
CREATE INDEX IF NOT EXISTS idx_reports_sim     ON reports(simulation_id);
CREATE INDEX IF NOT EXISTS idx_reports_project ON reports(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_type      ON tasks(task_type);
```

- [ ] **Step 2: Write the bootstrap module**

Create `backend/app/db/bootstrap.py`:

```python
"""Database bootstrap: apply schema and recover orphaned tasks on startup.

The DB is disposable — schema is idempotent (CREATE TABLE IF NOT EXISTS), and
the file-based content is authoritative, so there is no migration framework.
"""

import os

from ..config import Config
from ..utils.logger import get_logger
from .connection import get_conn

logger = get_logger('mirofish.db')

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def _apply_schema() -> None:
    """Create tables/indexes if they don't exist (idempotent)."""
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with open(_SCHEMA_PATH, 'r', encoding='utf-8') as f:
        ddl = f.read()
    conn = get_conn()
    conn.executescript(ddl)
    conn.commit()


def init_db(app=None) -> None:
    """Run at app startup: apply schema, then recover orphaned tasks."""
    _apply_schema()
    recovered = recover_orphaned_tasks()
    if recovered:
        logger.info(f"Recovered {recovered} orphaned task(s) after restart")


def recover_orphaned_tasks() -> int:
    """A task still marked 'processing'/'pending' at startup had its thread
    killed by the restart. Mark such tasks failed so the UI stops spinning;
    the on-disk report sections remain, enabling Resume.

    Returns the number of tasks transitioned.
    """
    from datetime import datetime
    conn = get_conn()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE tasks SET status='failed', "
        "error=COALESCE(error,'Interrupted by backend restart'), updated_at=? "
        "WHERE status IN ('processing','pending')",
        (now,),
    )
    conn.commit()
    return cur.rowcount
```

- [ ] **Step 3: Add a schema test**

Append to `backend/tests/test_connection.py`:

```python
def test_schema_tables_exist():
    # conftest applies the schema for every test
    conn = get_conn()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert {"projects", "simulations", "reports", "tasks"} <= names
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_connection.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/schema.sql backend/app/db/bootstrap.py backend/tests/test_connection.py
git commit -m "feat(db): schema + idempotent bootstrap with orphaned-task recovery"
```

---

## Task 4: Task repository

**Files:**
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/task_repo.py`
- Test: `backend/tests/test_task_repo.py`

- [ ] **Step 1: Create repositories package marker**

Create `backend/app/repositories/__init__.py` (empty file):

```python
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_task_repo.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_task_repo.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.repositories.task_repo'`)

- [ ] **Step 4: Implement the task repository**

Create `backend/app/repositories/task_repo.py`:

```python
"""CRUD + cancellation + recovery queries on the `tasks` table.

Stores task state durably (replacing the old in-memory dict). Returns plain
dicts with JSON columns parsed and the cancel flag coerced to bool.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..db.connection import get_conn

_JSON_FIELDS = ("result", "metadata")


def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    for field in _JSON_FIELDS:
        raw = d.get(field)
        d[field] = json.loads(raw) if raw else ({} if field == "metadata" else None)
    d["cancel_requested"] = bool(d.get("cancel_requested", 0))
    return d


def create(task_id: str, task_type: str, metadata: Optional[Dict] = None) -> None:
    now = datetime.now().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO tasks (task_id, task_type, status, progress, metadata, "
        "created_at, updated_at) VALUES (?, ?, 'pending', 0, ?, ?, ?)",
        (task_id, task_type, json.dumps(metadata or {}), now, now),
    )
    conn.commit()


def get(task_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    return _row_to_dict(row) if row else None


_UPDATABLE = {"status", "progress", "message", "result", "error", "metadata"}


def update(task_id: str, **fields) -> None:
    sets, params = [], []
    for key, value in fields.items():
        if key not in _UPDATABLE:
            continue
        if key in _JSON_FIELDS:
            value = json.dumps(value) if value is not None else None
        sets.append(f"{key}=?")
        params.append(value)
    if not sets:
        return
    sets.append("updated_at=?")
    params.append(datetime.now().isoformat())
    params.append(task_id)
    conn = get_conn()
    conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE task_id=?", params)
    conn.commit()


def request_cancel(task_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE tasks SET cancel_requested=1, updated_at=? WHERE task_id=?",
        (datetime.now().isoformat(), task_id),
    )
    conn.commit()


def is_cancel_requested(task_id: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT cancel_requested FROM tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    return bool(row["cancel_requested"]) if row else False


def list(task_type: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_conn()
    if task_type:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE task_type=? ORDER BY created_at DESC",
            (task_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def find_processing() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status IN ('processing','pending')"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_task_repo.py -v`
Expected: PASS (8 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/__init__.py backend/app/repositories/task_repo.py backend/tests/test_task_repo.py
git commit -m "feat(db): task repository (CRUD, cancel flag, recovery queries)"
```

---

## Task 5: DB-backed TaskManager (keep public signatures)

**Files:**
- Modify: `backend/app/models/task.py`
- Test: `backend/tests/test_task_manager.py`

The `Task` dataclass and `TaskStatus` enum stay. `TaskManager`'s methods keep identical signatures (`create_task`, `get_task`, `update_task`, `complete_task`, `fail_task`, `list_tasks`) so `api/graph.py` and `api/report.py` callers are untouched — only the storage changes from an in-memory dict to `task_repo`. Two new pass-through helpers (`request_cancel`, `is_cancel_requested`) are added for later cancellation work.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_task_manager.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_task_manager.py -v`
Expected: FAIL (`test_survives_new_manager_instance` and others — the current in-memory manager won't roundtrip via the DB / cancel helpers don't exist)

- [ ] **Step 3: Rewrite TaskManager to delegate to task_repo**

Replace the entire body of `backend/app/models/task.py` with:

```python
"""
Task status management
Durable, SQLite-backed task store (replaces the former in-memory singleton).
The Task dataclass and method signatures are unchanged so callers don't change.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from ..repositories import task_repo


class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Task data class"""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    progress_detail: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


def _row_to_task(row: Dict[str, Any]) -> Task:
    def _dt(value):
        try:
            return datetime.fromisoformat(value) if value else datetime.now()
        except (ValueError, TypeError):
            return datetime.now()

    return Task(
        task_id=row["task_id"],
        task_type=row["task_type"],
        status=TaskStatus(row["status"]),
        created_at=_dt(row.get("created_at")),
        updated_at=_dt(row.get("updated_at")),
        progress=row.get("progress", 0) or 0,
        message=row.get("message") or "",
        result=row.get("result"),
        error=row.get("error"),
        metadata=row.get("metadata") or {},
    )


class TaskManager:
    """Durable task manager backed by the tasks table."""

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        task_id = str(uuid.uuid4())
        task_repo.create(task_id, task_type, metadata or {})
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        row = task_repo.get(task_id)
        return _row_to_task(row) if row else None

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict] = None,
    ):
        fields: Dict[str, Any] = {}
        if status is not None:
            fields["status"] = status.value if isinstance(status, TaskStatus) else status
        if progress is not None:
            fields["progress"] = progress
        if message is not None:
            fields["message"] = message
        if result is not None:
            fields["result"] = result
        if error is not None:
            fields["error"] = error
        # progress_detail is accepted for signature compatibility; not indexed.
        if fields:
            task_repo.update(task_id, **fields)

    def complete_task(self, task_id: str, result: Dict):
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Task completed",
            result=result,
        )

    def fail_task(self, task_id: str, error: str):
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            error=error,
        )

    def list_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return [_row_to_task(r).to_dict() for r in task_repo.list(task_type=task_type)]

    # --- cancellation pass-throughs (used by later cancel features) ---

    def request_cancel(self, task_id: str) -> None:
        task_repo.request_cancel(task_id)

    def is_cancel_requested(self, task_id: str) -> bool:
        return task_repo.is_cancel_requested(task_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_task_manager.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Verify the existing callers still type-check at the call sites**

Run: `cd backend && .venv/bin/python -c "import app.api.graph, app.api.report; print('imports ok')"`
Expected: prints `imports ok` (note: `list_tasks` in `api/graph.py:644` iterates results and calls `.to_dict()`; that line becomes double-conversion — fixed in Task 7).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/task.py backend/tests/test_task_manager.py
git commit -m "feat(db): make TaskManager durable via task_repo (signatures unchanged)"
```

---

## Task 6: Crash-recovery behavior test

**Files:**
- Test: `backend/tests/test_recovery.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_recovery.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_recovery.py -v`
Expected: PASS (3 passed) — `recover_orphaned_tasks` was implemented in Task 3; this task locks in its behavior against the real `TaskManager`.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_recovery.py
git commit -m "test(db): crash-recovery transitions orphaned tasks to failed"
```

---

## Task 7: Wire startup + normalize graph-build task_type

**Files:**
- Modify: `backend/app/__init__.py:64` (after `log_response`, before blueprint registration)
- Modify: `backend/app/api/graph.py:447`
- Modify: `backend/app/api/graph.py:644`

- [ ] **Step 1: Call `init_db()` in the app factory**

In `backend/app/__init__.py`, immediately after the `log_response` function definition (line 63) and before the `# Register blueprints` comment (line 65), add:

```python
    # Initialize the SQLite index DB (schema + crash recovery) before serving
    from .db.bootstrap import init_db
    init_db(app)
    if should_log_startup:
        logger.info("Database index initialized")
```

- [ ] **Step 2: Normalize the graph-build task_type**

In `backend/app/api/graph.py`, replace line 447:

```python
        task_id = task_manager.create_task(f"Build graph: {graph_name}")
```

with:

```python
        task_id = task_manager.create_task(
            "graph_build",
            metadata={"label": f"Build graph: {graph_name}", "project_id": project_id},
        )
```

- [ ] **Step 3: Fix the double-conversion in list_tasks**

In `backend/app/api/graph.py`, the `list_tasks` route (around line 644) currently does:

```python
    tasks = TaskManager().list_tasks()

    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })
```

`TaskManager.list_tasks()` now already returns dicts, so replace those lines with:

```python
    tasks = TaskManager().list_tasks()

    return jsonify({
        "success": True,
        "data": tasks,
        "count": len(tasks)
    })
```

- [ ] **Step 4: Verify the app boots and creates the DB**

Run: `cd backend && .venv/bin/python -c "from app import create_app; create_app(); import os; from app.config import Config; print('db exists:', os.path.exists(Config.DB_PATH))"`
Expected: prints `db exists: True` (and no traceback). This creates the real `uploads/mirofish.db`.

- [ ] **Step 5: Run the full test suite**

Run: `cd backend && .venv/bin/python -m pytest -v`
Expected: PASS (all tests from Tasks 2–6 green)

- [ ] **Step 6: Commit**

```bash
git add backend/app/__init__.py backend/app/api/graph.py
git commit -m "feat(db): init DB at startup; normalize graph_build task_type"
```

---

## Task 8: Manual end-to-end durability check

**Files:** none (verification only)

- [ ] **Step 1: Confirm a task survives a simulated restart**

Run this script from `backend/`:

```bash
cd backend && .venv/bin/python - <<'PY'
from app import create_app
create_app()  # applies schema + recovery against the real uploads/mirofish.db
from app.models.task import TaskManager, TaskStatus
tm = TaskManager()
tid = tm.create_task("graph_build", {"project_id": "demo"})
tm.update_task(tid, status=TaskStatus.PROCESSING, progress=50)
print("before restart:", tm.get_task(tid).status, tm.get_task(tid).progress)

# Simulate a restart: drop this thread's connection, re-run startup recovery.
from app.db.connection import close_conn
close_conn()
from app.db.bootstrap import recover_orphaned_tasks
print("recovered:", recover_orphaned_tasks())
print("after restart:", tm.get_task(tid).status, "|", tm.get_task(tid).error)
PY
```

Expected output:
```
before restart: TaskStatus.PROCESSING 50
recovered: 1
after restart: TaskStatus.FAILED | Interrupted by backend restart
```

- [ ] **Step 2: Clean up the demo task from the real DB**

Run: `cd backend && .venv/bin/python -c "from app import create_app; create_app(); from app.db.connection import get_conn; c=get_conn(); c.execute(\"DELETE FROM tasks WHERE json_extract(metadata,'\$.project_id')='demo'\"); c.commit(); print('cleaned')"`
Expected: prints `cleaned`

---

## Self-Review

**Spec coverage (this plan's slice):**
- Concurrency model (WAL, per-thread conn, pragmas) → Task 2 ✓
- Full schema incl. preferences/usage columns → Task 3 ✓
- Durable task state (the headline fix) → Tasks 4–5 ✓
- Universal cancel flag on tasks (`request_cancel`/`is_cancel_requested`) → Tasks 4–5 ✓ (consumers wired in the follow-on cancel plan)
- Disposable DB / idempotent schema → Task 3 ✓
- Crash recovery → Tasks 3, 6, 8 ✓
- Startup wiring + `graph_build` task_type normalization → Task 7 ✓
- `Config.DB_PATH` → Task 1 ✓

**Deferred to follow-on plans (not this plan):** project/simulation/report repositories + Manager content-seam; `rebuild_index.py`; preferences modal + `ReportAgent` wiring; cancellation consumers (graph build `cancel_check`, report/sim UI); project delete-cascade/rename/archive; usage on report view. These depend only on the foundation laid here.

**Placeholder scan:** none — every step has concrete code/commands.

**Type consistency:** `task_repo.create(task_id, task_type, metadata)` / `get`/`update`/`request_cancel`/`is_cancel_requested`/`list`/`find_processing` are used identically in `TaskManager` and tests. `Task.to_dict()` keys unchanged from the original. `recover_orphaned_tasks()` returns an int (`cur.rowcount`), asserted in Task 6.
