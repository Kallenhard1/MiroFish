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
