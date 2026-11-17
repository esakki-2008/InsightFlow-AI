from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """An account that owns private InsightFlow records."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class AnalysisHistory(Base):
    """Metadata and compact result summary for a completed analysis."""

    __tablename__ = "analysis_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DatasetRecord(Base):
    """Persistent metadata for an inspected dataset; never stores source rows or file bytes."""

    __tablename__ = "dataset_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)
    columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    data_types: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    missing_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    total_missing_values: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )


class MLModelRecord(Base):
    """Persistent metadata for a trained model bundle; estimator binaries remain in artifacts."""

    __tablename__ = "ml_model_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    dataset_filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_column: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
    test_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    class_labels: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    model_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metrics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )


class AIProviderCredential(Base):
    """Encrypted provider credential owned by exactly one account."""

    __tablename__ = "ai_provider_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    protocol: Mapped[str] = mapped_column(String(32), nullable=False, default="openai_compatible")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_custom_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_last_four: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
