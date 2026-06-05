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


def test_schema_tables_exist():
    # conftest applies the schema for every test
    conn = get_conn()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert {"projects", "simulations", "reports", "tasks"} <= names
