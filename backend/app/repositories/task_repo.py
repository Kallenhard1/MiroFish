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
