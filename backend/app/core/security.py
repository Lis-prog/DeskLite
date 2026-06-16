from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt for storage."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        # Malformed/legacy hash — treat as a failed check rather than crashing.
        return False


def _create_token(
    *,
    subject: int,
    role: str,
    email: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "email": email,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(*, subject: int, role: str, email: str) -> str:
    """Short-lived token used to authorize API calls."""
    return _create_token(
        subject=subject,
        role=role,
        email=email,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(*, subject: int, role: str, email: str) -> str:
    """Long-lived token used to mint new access tokens."""
    return _create_token(
        subject=subject,
        role=role,
        email=email,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_days),
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Validate a JWT and return its claims. Raises ValueError on bad/wrong-type tokens."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Wrong token type")
    if payload.get("sub") is None or payload.get("role") is None:
        raise ValueError("Missing claims")
    return payload
