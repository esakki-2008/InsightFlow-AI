"""Add email authentication and nullable ownership links.

Existing ownerless records deliberately remain unassigned. They must not be
exposed to the first account that registers.
"""
from alembic import op
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, inspect, text

revision = "0002_auth_and_ownership"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            Column("id", String(length=36), primary_key=True),
            Column("email", String(length=254), nullable=False, unique=True),
            Column("password_hash", String(length=255), nullable=False),
            Column("is_active", Boolean(), nullable=False, server_default=text("1")),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    for table in ("analysis_history", "dataset_registry", "ml_model_registry"):
        if table not in tables:
            continue

        columns = {column["name"] for column in inspect(bind).get_columns(table)}
        if "user_id" not in columns:
            # Batch mode uses SQLite's safe table-copy strategy to add a
            # nullable FK while preserving every pre-existing row.
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(
                    Column(
                        "user_id",
                        String(length=36),
                        ForeignKey("users.id"),
                        nullable=True,
                    )
                )

        indexes = {index["name"] for index in inspect(bind).get_indexes(table)}
        index_name = f"ix_{table}_user_id"
        if index_name not in indexes:
            op.create_index(index_name, table, ["user_id"], unique=False)


def downgrade() -> None:
    # Preserve user and ownership data rather than risk destructive rollback.
    pass
