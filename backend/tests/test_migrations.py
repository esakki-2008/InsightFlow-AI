"""Integration tests for fresh-install and legacy-database Alembic upgrades."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _upgrade_database(database_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Alembic upgrade failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_fresh_database_migrates_to_head_and_upgrade_is_idempotent(tmp_path):
    database_path = tmp_path / "fresh-insightflow.db"

    _upgrade_database(database_path)
    _upgrade_database(database_path)

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "users",
            "analysis_history",
            "dataset_registry",
            "ml_model_registry",
            "ai_provider_credentials",
            "alembic_version",
        }.issubset(tables)

        for table in ("analysis_history", "dataset_registry", "ml_model_registry"):
            columns = {column["name"] for column in inspector.get_columns(table)}
            assert "user_id" in columns
            indexes = {index["name"] for index in inspector.get_indexes(table)}
            assert f"ix_{table}_user_id" in indexes

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "0003_ai_provider_credentials"
    finally:
        engine.dispose()


def test_legacy_database_upgrade_preserves_ownerless_history(tmp_path):
    database_path = tmp_path / "legacy-insightflow.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE analysis_history (
                id VARCHAR(36) PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                analysis_type VARCHAR(80) NOT NULL,
                row_count INTEGER,
                column_count INTEGER,
                summary JSON NOT NULL,
                created_at DATETIME NOT NULL,
                notes TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO analysis_history
                (id, filename, analysis_type, row_count, column_count, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-history-001",
                "legacy.csv",
                "Data Quality",
                12,
                3,
                '{"legacy": true}',
                "2025-01-01 00:00:00",
            ),
        )

    _upgrade_database(database_path)

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with engine.connect() as connection:
            legacy = connection.execute(
                text(
                    "SELECT id, filename, user_id, summary "
                    "FROM analysis_history WHERE id = :record_id"
                ),
                {"record_id": "legacy-history-001"},
            ).mappings().one()
        assert legacy["filename"] == "legacy.csv"
        assert legacy["user_id"] is None
        assert legacy["summary"] == '{"legacy": true}'
    finally:
        engine.dispose()
