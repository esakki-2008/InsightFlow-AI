"""Authenticated encryption for user-supplied AI provider credentials."""
import os

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException


def _fernet() -> Fernet:
    configured_key = os.getenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="Credential encryption is not configured. Set INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY.",
        )
    try:
        return Fernet(configured_key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Credential encryption key is invalid. Generate a Fernet key and configure it securely.",
        ) from exc


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key; plaintext is never written to the database."""
    if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 4096:
        raise ValueError("Enter a valid API key (maximum 4096 characters).")
    return _fernet().encrypt(api_key.strip().encode("utf-8")).decode("ascii")


def decrypt_api_key(encrypted_api_key: str) -> str:
    """Decrypt a credential for server-side provider calls only."""
    try:
        return _fernet().decrypt(encrypted_api_key.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="This saved credential cannot be decrypted. Verify the configured encryption key.",
        ) from exc
