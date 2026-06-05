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
