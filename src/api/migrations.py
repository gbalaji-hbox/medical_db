"""
Database migration runner.

Can be invoked standalone before starting the server:
    python -m src.api.migrations

Or called automatically via init_db() at server startup.

To add a schema change:
  1. Append a new (version, description, sql) tuple to MIGRATIONS below.
  2. Never edit or reorder existing entries — only append.
  3. SQLite supports: CREATE TABLE, CREATE INDEX, ALTER TABLE ADD COLUMN.
     For destructive changes (DROP, rename) create a new table + INSERT SELECT.
"""

import logging
import sqlite3
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Migration definitions — append only
# ---------------------------------------------------------------------------

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "initial schema: jobs, audit_log, users, api_keys",
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            applied_at  REAL    NOT NULL,
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
            ts          REAL    NOT NULL,
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
        """,
    ),
    # Add future migrations here, e.g.:
    # (2, "add last_login_at to users", "ALTER TABLE users ADD COLUMN last_login_at REAL;"),
    # (3, "add priority to jobs",       "ALTER TABLE jobs  ADD COLUMN priority INTEGER DEFAULT 0;"),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, 0 if schema_version doesn't exist yet."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] or 0
    except sqlite3.OperationalError:
        return 0


def run(conn: sqlite3.Connection) -> None:
    """Apply all pending migrations to the given connection."""
    current = _current_version(conn)
    pending = [(v, desc, sql) for v, desc, sql in MIGRATIONS if v > current]

    if not pending:
        logger.info("DB schema is up to date (version %d)", current)
        return

    for version, description, sql in pending:
        logger.info("Applying migration v%d: %s", version, description)
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
            (version, time.time(), description),
        )
        conn.commit()
        logger.info("Migration v%d applied successfully", version)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    from src.api.config import DB_PATH

    logger.info("DB path: %s", DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        run(conn)
        version = _current_version(conn)
        logger.info("Schema version after migration: %d", version)
    except Exception as exc:
        logger.error("Migration failed: %s", exc)
        sys.exit(1)
    finally:
        conn.close()
