"""Per-user CRUD API for encrypted OpenAI-compatible provider credentials."""
from datetime import datetime, timezone
import ipaddress
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AIProviderCredential, User
from app.services.credential_crypto_service import decrypt_api_key, encrypt_api_key
from app.services.openai_compatible_service import test_openai_compatible_connection
from app.services.native_provider_service import (
    PROTOCOL_GEMINI, PROTOCOL_ANTHROPIC, test_native_provider_connection,
)

router = APIRouter(prefix="/api/v1/ai/credentials", tags=["AI provider credentials"])


def _validate_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter a valid HTTPS provider base URL without credentials, query parameters, or fragments.")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal provider endpoints are not allowed.")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("Use a public provider hostname, not an IP address.")
    return value


class CredentialCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    provider_name: str = Field(min_length=1, max_length=80)
    protocol: str = Field(default="openai_compatible", pattern="^(openai_compatible|native_gemini|native_anthropic)$")
    base_url: str = Field(min_length=8, max_length=500)
    model_id: str = Field(min_length=1, max_length=200)
    api_key: str = Field(min_length=1, max_length=4096)

    @field_validator("display_name", "provider_name", "model_id")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url_shape(cls, value: str) -> str:
        return _validate_base_url(value)

    @field_validator("api_key")
    @classmethod
    def trim_api_key(cls, value: str) -> str:
        value = value.strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("API keys cannot be blank or contain whitespace.")
        return value


class CredentialUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    provider_name: str | None = Field(default=None, min_length=1, max_length=80)
    base_url: str | None = Field(default=None, min_length=8, max_length=500)
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)

    @field_validator("display_name", "provider_name", "model_id")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_optional_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_base_url(value)

    @field_validator("api_key")
    @classmethod
    def trim_optional_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("API keys cannot be blank or contain whitespace.")
        return value


def _credential_response(record: AIProviderCredential) -> dict:
    """Return safe metadata only; never serialize encrypted or plaintext key material."""
    return {
        "id": record.id,
        "display_name": record.display_name,
        "provider_name": record.provider_name,
        "protocol": record.protocol,
        "base_url": record.base_url,
        "model_id": record.model_id,
        "has_api_key": True,
        "key_hint": f"••••{record.key_last_four}",
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _owned_credential(db: Session, credential_id: str, user: User) -> AIProviderCredential:
    record = (
        db.query(AIProviderCredential)
        .filter(
            AIProviderCredential.id == credential_id,
            AIProviderCredential.user_id == user.id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="AI provider credential not found.")
    return record


@router.post("", status_code=201)
def create_credential(
    payload: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    encrypted_key = encrypt_api_key(payload.api_key)
    record = AIProviderCredential(
        id=str(uuid4()),
        user_id=current_user.id,
        display_name=payload.display_name,
        provider_name=payload.provider_name,
        protocol=payload.protocol,
        base_url=payload.base_url,
        model_id=payload.model_id,
        encrypted_api_key=encrypted_key,
        key_last_four=payload.api_key[-4:],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "Provider credential saved securely.", "credential": _credential_response(record)}


@router.get("")
def list_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(AIProviderCredential)
        .filter(AIProviderCredential.user_id == current_user.id)
        .order_by(AIProviderCredential.created_at.desc())
        .all()
    )
    return {"items": [_credential_response(record) for record in records]}


@router.patch("/{credential_id}")
def update_credential(
    credential_id: str,
    payload: CredentialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _owned_credential(db, credential_id, current_user)
    changes = payload.model_dump(exclude_unset=True)
    new_key = changes.pop("api_key", None)
    for field, value in changes.items():
        setattr(record, field, value)
    if new_key is not None:
        record.encrypted_api_key = encrypt_api_key(new_key)
        record.key_last_four = new_key[-4:]
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return {"message": "Provider credential updated.", "credential": _credential_response(record)}


@router.delete("/{credential_id}")
def delete_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _owned_credential(db, credential_id, current_user)
    db.delete(record)
    db.commit()
    return {"message": "Provider credential deleted.", "id": credential_id}


@router.post("/{credential_id}/test")
def test_saved_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test a saved provider credential without returning its decrypted API key."""
    record = _owned_credential(db, credential_id, current_user)
    api_key = decrypt_api_key(record.encrypted_api_key)
    try:
        if record.protocol == "openai_compatible":
            return test_openai_compatible_connection(
                api_key=api_key,
                base_url=record.base_url,
                model=record.model_id,
                provider_name=record.provider_name,
            )
        if record.protocol in {PROTOCOL_GEMINI, PROTOCOL_ANTHROPIC}:
            return test_native_provider_connection(
                protocol=record.protocol,
                api_key=api_key,
                base_url=record.base_url,
                model=record.model_id,
                provider_name=record.provider_name,
            )
        raise ValueError("The saved provider protocol is not supported.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
