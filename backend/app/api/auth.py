from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import _UserStub, get_current_user, require_roles
from app.core.rate_limit import enforce_auth_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_base(*, path: str) -> dict[str, object]:
    """Shared Set-Cookie attributes; optional domain for app+api subdomain deploys."""
    base: dict[str, object] = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": path,
    }
    domain = settings.cookie_domain.strip()
    if domain:
        base["domain"] = domain
    return base


def _set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str
) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_minutes * 60,
        **_cookie_base(path="/"),
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        **_cookie_base(path="/api/v1/auth"),
    )


def _clear_auth_cookies(response: Response) -> None:
    access = _cookie_base(path="/")
    refresh = _cookie_base(path="/api/v1/auth")
    response.delete_cookie(key="access_token", **access)
    response.delete_cookie(key="refresh_token", **refresh)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
) -> User:
    """Self-service sign-up. New accounts are always created as 'customer';
    role is never accepted from the request body (anti privilege-escalation)."""
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(enforce_auth_rate_limit),
) -> TokenResponse:
    """Exchange email + password for JWT access and refresh tokens.

    Valid credentials issue both tokens (also set as httpOnly cookies);
    invalid credentials always return 401 with a generic message so we
    never reveal whether the email exists (anti user-enumeration)."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=user.id, role=user.role, email=user.email
    )
    refresh_token = create_refresh_token(
        subject=user.id, role=user.role, email=user.email
    )
    _set_auth_cookies(
        response, access_token=access_token, refresh_token=refresh_token
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    _current_user: _UserStub = Depends(get_current_user),
) -> None:
    """End the session by clearing auth cookies. Requires a valid access token."""
    _clear_auth_cookies(response)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    request: Request,
    response: Response,
    _rate_limit: None = Depends(enforce_auth_rate_limit),
) -> TokenResponse:
    """Exchange a valid refresh cookie for a new access token (and rotated refresh)."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    refresh_token = request.cookies.get("refresh_token")
    if refresh_token is None:
        raise credentials_exc from None

    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except ValueError:
        raise credentials_exc from None

    user_id = int(payload["sub"])
    role = payload["role"]
    email = payload.get("email") or ""

    access_token = create_access_token(subject=user_id, role=role, email=email)
    new_refresh_token = create_refresh_token(
        subject=user_id, role=role, email=email
    )
    _set_auth_cookies(
        response, access_token=access_token, refresh_token=new_refresh_token
    )

    return TokenResponse(
        access_token=access_token, refresh_token=new_refresh_token
    )


@router.get("/me", response_model=UserRead)
def me(
    current_user: _UserStub = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated user's profile."""
    user = db.get(User, current_user.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


@router.get("/admin/ping")
def admin_ping(
    current_user: _UserStub = Depends(require_roles("admin")),
) -> dict[str, str]:
    """Admin-only smoke route for verifying role-gated auth."""
    return {"status": "ok", "role": current_user.role}
