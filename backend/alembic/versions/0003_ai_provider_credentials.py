"""Add per-user encrypted AI provider credentials."""
from alembic import op
import sqlalchemy as sa

revision = "0003_ai_provider_credentials"
down_revision = "0002_auth_and_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_credentials",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("protocol", sa.String(length=32), nullable=False, server_default="openai_compatible"),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("key_last_four", sa.String(length=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ai_provider_credentials_user_id",
        "ai_provider_credentials",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_provider_credentials_user_id", table_name="ai_provider_credentials")
    op.drop_table("ai_provider_credentials")
