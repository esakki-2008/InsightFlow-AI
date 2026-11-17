"""Email/password authentication and bearer-token verification."""
import hashlib
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pwdlib import PasswordHash
import redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "insightflow-ai"
ACCESS_TOKEN_MINUTES = 30

# Shared Redis sliding-window limits are used when REDIS_URL is configured.
# Local development can fall back to process memory. Production must use Redis.
AUTH_RATE_LIMITS = {
    "login": (5, 15 * 60),
    "register": (3, 60 * 60),
}
_rate_limit_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_rate_limit_lock = threading.Lock()
_redis_client = None
_redis_client_lock = threading.Lock()

_REDIS_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local member = ARGV[4]
redis.call("ZREMRANGEBYSCORE", key, "-inf", now_ms - window_ms)
local count = redis.call("ZCARD", key)
if count >= max_requests then
    local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
    local retry_ms = math.max(1, tonumber(oldest[2]) + window_ms - now_ms)
    return {0, math.ceil(retry_ms / 1000)}
end
redis.call("ZADD", key, now_ms, member)
redis.call("PEXPIRE", key, window_ms)
return {1, 0}
"""


def _get_redis_client():
    """Create one bounded-timeout Redis client per application process."""
    global _redis_client
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    with _redis_client_lock:
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(
                url,
                socket_connect_timeout=1,
                socket_timeout=1,
                health_check_interval=30,
                decode_responses=True,
            )
    return _redis_client


def reset_auth_rate_limits() -> None:
    """Clear local counters and reset the client cache; used by isolated tests."""
    global _redis_client
    with _rate_limit_lock:
        _rate_limit_events.clear()
    with _redis_client_lock:
        _redis_client = None


def _raise_rate_limited(retry_after: int) -> None:
    raise HTTPException(
        status_code=429,
        detail="Too many authentication attempts. Please try again later.",
        headers={"Retry-After": str(max(1, retry_after))},
    )


def _enforce_local_rate_limit(action: str, client_ip: str, limit: int, window_seconds: int) -> None:
    key = (action, client_ip)
    now = time.monotonic()
    with _rate_limit_lock:
        events = _rate_limit_events[key]
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            _raise_rate_limited(int(window_seconds - (now - events[0]) + 0.999))
        events.append(now)


def _enforce_auth_rate_limit(request: Request, action: str) -> None:
    limit, window_seconds = AUTH_RATE_LIMITS[action]
    client_ip = request.client.host if request.client else "unknown"
    redis_url = os.getenv("REDIS_URL", "").strip()
    environment = os.getenv("INSIGHTFLOW_ENV", "development").strip().lower()

    if not redis_url and environment in {"production", "prod"}:
        raise HTTPException(
            status_code=503,
            detail="Shared authentication rate limiting is not configured. Set REDIS_URL.",
        )

    if redis_url:
        try:
            client = _get_redis_client()
            ip_digest = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
            key = f"insightflow:auth-rate-limit:{action}:{ip_digest}"
            now_ms = int(time.time() * 1000)
            result = client.eval(
                _REDIS_RATE_LIMIT_SCRIPT,
                1,
                key,
                now_ms,
                window_seconds * 1000,
                limit,
                f"{now_ms}:{time.time_ns()}",
            )
            if int(result[0]) == 0:
                _raise_rate_limited(int(result[1]))
            return
        except HTTPException:
            raise
        except (redis.RedisError, ValueError) as exc:
            # Fail closed when a shared limiter was explicitly configured.
            raise HTTPException(
                status_code=503,
                detail="Authentication rate limiting is temporarily unavailable.",
            ) from exc

    _enforce_local_rate_limit(action, client_ip, limit, window_seconds)


class AuthCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime


def _jwt_secret() -> str:
    secret = os.getenv("INSIGHTFLOW_JWT_SECRET", "")
    if (
        len(secret.encode("utf-8")) < 32
        or secret != secret.strip()
        or secret.lower() in {"change-me", "changeme", "your-secret", "secret"}
    ):
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured. Set a strong INSIGHTFLOW_JWT_SECRET.",
        )
    return secret


def _create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(
            credentials.credentials,
            _jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["sub", "exp", "iat", "iss"]},
        )
        user_id = payload.get("sub")
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token.", headers={"WWW-Authenticate": "Bearer"})
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or inactive account.", headers={"WWW-Authenticate": "Bearer"})
    return user


@router.post("/register", status_code=201)
def register(credentials: AuthCredentials, request: Request, db: Session = Depends(get_db)):
    _enforce_auth_rate_limit(request, "register")
    _jwt_secret()
    existing = db.query(User).filter(User.email == credentials.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(
        email=credentials.email,
        password_hash=password_hasher.hash(credentials.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    db.refresh(user)
    return {
        "message": "Account created successfully.",
        "access_token": _create_access_token(user),
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(mode="json"),
    }


@router.post("/login")
def login(credentials: AuthCredentials, request: Request, db: Session = Depends(get_db)):
    _enforce_auth_rate_limit(request, "login")
    _jwt_secret()
    user = db.query(User).filter(User.email == credentials.email).first()
    if user is None or not user.is_active or not password_hasher.verify(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {
        "access_token": _create_access_token(user),
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(mode="json"),
    }


@router.get("/me", response_model=UserResponse)
def get_my_account(current_user: User = Depends(get_current_user)):
    return current_user
