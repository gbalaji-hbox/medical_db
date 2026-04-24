"""
SQLite connection manager, schema initialisation, and lightweight migrations.

Thread-local connections with WAL mode allow concurrent reads from multiple
threads without writer blocking. Call init_db() once at startup.
Swap DB_PATH for a PostgreSQL DSN and swap sqlite3 calls to psycopg2 to migrate.

Schema versioning:
  _MIGRATIONS is an ordered list of (version, sql) tuples.
  init_db() applies any migrations with version > current db version in order.
  To add a schema change: append a new entry to _MIGRATIONS — never edit existing ones.
"""

import logging
import sqlite3
import threading
import time

import bcrypt

from src.api.config import DB_PATH

logger = logging.getLogger(__name__)

# Default master admin seeded on first startup.
# Password: HBox@123456!  — change via the user-management API after first login.
_DEFAULT_ADMIN_USERNAME = "admin"
_DEFAULT_ADMIN_HASH = "$2b$12$qoeQCjmv1taeroeFqhzEiejs4nixy2E7VgUlvcbg/cqOlvpREzELy"

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


# ---------------------------------------------------------------------------
# Schema migrations — append only, never edit existing entries.
# Each entry: (version: int, sql: str)
# ---------------------------------------------------------------------------

_MIGRATIONS: list[tuple[int, str]] = [
    (1, """
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            applied_at  REAL NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            job_id       TEXT PRIMARY KEY,
            module       TEXT NOT NULL,
            status       TEXT NOT NULL,
            created_at   REAL NOT NULL,
            started_at   REAL,
            finished_at  REAL,
            output_file  TEXT,
            log          TEXT,
            returncode   INTEGER,
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
            key_id       TEXT PRIMARY KEY,
            key_hash     TEXT NOT NULL UNIQUE,
            name         TEXT NOT NULL,
            created_by   TEXT NOT NULL,
            created_at   REAL NOT NULL,
            last_used_at REAL,
            is_active    INTEGER NOT NULL DEFAULT 1,
            role         TEXT NOT NULL DEFAULT 'user'
        );
    """),
    # Future schema changes go here, e.g.:
    # (2, "ALTER TABLE users ADD COLUMN last_login_at REAL;"),
    # (3, "ALTER TABLE jobs ADD COLUMN priority INTEGER DEFAULT 0;"),
]


def _current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 if none."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] or 0
    except sqlite3.OperationalError:
        return 0  # schema_version table doesn't exist yet


def _run_migrations(conn: sqlite3.Connection) -> None:
    current = _current_version(conn)
    pending = [(v, sql) for v, sql in _MIGRATIONS if v > current]
    if not pending:
        logger.debug("DB schema up to date (version %d)", current)
        return

    for version, sql in pending:
        logger.info("Applying DB migration version %d", version)
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
            (version, time.time(), f"migration_{version}"),
        )
        conn.commit()
        logger.info("Migration %d applied", version)


def init_db() -> None:
    """Apply pending migrations and seed the default admin user."""
    conn = get_conn()
    _run_migrations(conn)
    _seed_admin(conn)


def _seed_admin(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT 1 FROM users WHERE username = ?", (_DEFAULT_ADMIN_USERNAME,)
    ).fetchone()
    if existing:
        return

    conn.execute(
        "INSERT INTO users (username, hashed_password, role, created_at) VALUES (?,?,?,?)",
        (_DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_HASH, "admin", time.time()),
    )
    conn.commit()
    logger.info("Default admin user '%s' created", _DEFAULT_ADMIN_USERNAME)
