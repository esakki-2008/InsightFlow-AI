"""Add encrypted custom HTTP headers to saved AI provider credentials."""
from alembic import op
import sqlalchemy as sa

revision = "0004_encrypted_provider_headers"
down_revision = "0003_ai_provider_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("ai_provider_credentials")}
    if "encrypted_custom_headers" not in columns:
        op.add_column(
            "ai_provider_credentials",
            sa.Column("encrypted_custom_headers", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    # Retain encrypted metadata during rollback; intentionally non-destructive.
    pass
