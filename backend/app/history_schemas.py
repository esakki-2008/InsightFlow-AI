from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HistoryCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    analysis_type: str = Field(min_length=1, max_length=80)
    row_count: int | None = Field(default=None, ge=0)
    column_count: int | None = Field(default=None, ge=0)
    summary: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("filename", "analysis_type")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class HistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    analysis_type: str
    row_count: int | None
    column_count: int | None
    summary: dict[str, Any]
    created_at: str
    notes: str | None


class HistoryListResponse(BaseModel):
    items: list[HistoryResponse]
    total: int
    limit: int
    offset: int
