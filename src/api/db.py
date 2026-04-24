"""
SQLite connection manager.

Thread-local connections with WAL mode allow concurrent reads from multiple
threads without writer blocking. Call init_db() once at startup.
Swap DB_PATH for a PostgreSQL DSN and swap sqlite3 calls to psycopg2 to migrate.

Schema changes live in migrations.py — never edit this file for schema work.
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


def init_db() -> None:
    """Apply pending migrations and seed the default admin user."""
    from src.api import migrations  # local import avoids circular at module load
    conn = get_conn()
    migrations.run(conn)
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
