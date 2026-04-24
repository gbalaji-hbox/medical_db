"""Unit tests for the database migration runner."""

import pytest

from src.api.migrations import MIGRATIONS, _current_version, run


class TestCurrentVersion:
    def test_fresh_db_returns_zero(self, fresh_db):
        assert _current_version(fresh_db) == 0

    def test_returns_zero_when_schema_version_missing(self, fresh_db):
        # schema_version table doesn't exist yet — must not raise
        result = _current_version(fresh_db)
        assert result == 0

    def test_returns_correct_version_after_migration(self, fresh_db):
        run(fresh_db)
        assert _current_version(fresh_db) == max(v for v, *_ in MIGRATIONS)


class TestRunMigrations:
    def test_creates_all_tables(self, fresh_db):
        run(fresh_db)
        tables = {
            r[0]
            for r in fresh_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "jobs" in tables
        assert "audit_log" in tables
        assert "users" in tables
        assert "api_keys" in tables
        assert "schema_version" in tables

    def test_idempotent_on_second_run(self, fresh_db):
        run(fresh_db)
        run(fresh_db)  # must not raise or insert duplicate rows
        count = fresh_db.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        assert count == len(MIGRATIONS)

    def test_records_migration_in_schema_version(self, fresh_db):
        run(fresh_db)
        rows = fresh_db.execute(
            "SELECT version, description FROM schema_version ORDER BY version"
        ).fetchall()
        assert len(rows) == len(MIGRATIONS)
        # First migration should be v1
        assert rows[0]["version"] == 1

    def test_applied_at_is_set(self, fresh_db):
        run(fresh_db)
        row = fresh_db.execute("SELECT applied_at FROM schema_version WHERE version=1").fetchone()
        assert row["applied_at"] > 0


class TestMigrationsFormat:
    def test_migrations_are_ordered(self):
        versions = [v for v, *_ in MIGRATIONS]
        assert versions == sorted(versions), "MIGRATIONS must be in ascending version order"

    def test_versions_are_unique(self):
        versions = [v for v, *_ in MIGRATIONS]
        assert len(versions) == len(set(versions)), "Duplicate migration version found"

    def test_each_migration_has_description(self):
        for entry in MIGRATIONS:
            assert len(entry) == 3, "Each migration must be (version, description, sql)"
            _, desc, _ = entry
            assert isinstance(desc, str) and len(desc) > 0

    def test_each_migration_has_sql(self):
        for _, _, sql in MIGRATIONS:
            assert isinstance(sql, str) and len(sql.strip()) > 0
