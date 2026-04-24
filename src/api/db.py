"""
SQLite connection manager and schema initialisation.

Thread-local connections with WAL mode allow concurrent reads from multiple
threads without writer blocking. Call init_db() once at startup.
Swap DB_PATH for a PostgreSQL DSN and swap sqlite3 calls to psycopg2 to migrate.
"""

import sqlite3
import threading
import time

from src.api.config import ADMIN_PASSWORD, ADMIN_USERNAME, DB_PATH

_local = threading.local()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = _connect()
    return _local.conn


def get_db():
    """FastAPI dependency — yields a thread-local SQLite connection."""
    yield get_conn()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id      TEXT PRIMARY KEY,
    module      TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  REAL NOT NULL,
    started_at  REAL,
    finished_at REAL,
    output_file TEXT,
    log         TEXT,
    returncode  INTEGER,
    submitted_by TEXT DEFAULT 'unknown'
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    client_ip   TEXT,
    auth_type   TEXT,
    identity    TEXT,
    method      TEXT NOT NULL,
    path        TEXT NOT NULL,
    status_code INTEGER,
    duration_ms REAL
);

CREATE TABLE IF NOT EXISTS users (
    username        TEXT PRIMARY KEY,
    hashed_password TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user',
    created_at      REAL NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id      TEXT PRIMARY KEY,
    key_hash    TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    created_by  TEXT NOT NULL,
    created_at  REAL NOT NULL,
    last_used_at REAL,
    is_active   INTEGER NOT NULL DEFAULT 1,
    role        TEXT NOT NULL DEFAULT 'user'
);
"""


def init_db() -> None:
    """Create tables and seed the default admin user."""
    conn = get_conn()
    conn.executescript(_SCHEMA)
    conn.commit()
    _seed_admin(conn)


def _seed_admin(conn: sqlite3.Connection) -> None:
    from passlib.context import CryptContext  # local import — avoids circular

    existing = conn.execute(
        "SELECT 1 FROM users WHERE username = ?", (ADMIN_USERNAME,)
    ).fetchone()
    if existing:
        return

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    conn.execute(
        "INSERT INTO users (username, hashed_password, role, created_at) VALUES (?,?,?,?)",
        (ADMIN_USERNAME, pwd_ctx.hash(ADMIN_PASSWORD), "admin", time.time()),
    )
    conn.commit()
