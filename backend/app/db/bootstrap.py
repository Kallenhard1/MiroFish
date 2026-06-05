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
