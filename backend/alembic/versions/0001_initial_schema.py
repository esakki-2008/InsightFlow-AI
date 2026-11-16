"""Baseline the existing InsightFlow database schema.

This migration creates any missing application tables while preserving existing
tables and records. It supports both existing local databases and fresh installs.
"""
from alembic import op
from sqlalchemy import inspect

from app.database import Base
from app import models  # noqa: F401 - register all ORM tables

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    missing_tables = [
        table for table in Base.metadata.sorted_tables
        if table.name not in existing_tables
    ]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables)


def downgrade() -> None:
    # Intentionally non-destructive: this baseline may have adopted tables
    # containing user data that existed before Alembic was introduced.
    pass
