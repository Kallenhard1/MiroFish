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
