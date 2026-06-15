from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["customer", "agent", "admin"]


class UserCreate(BaseModel):
    """Writable fields for sign-up. Note: no `role` — clients cannot set it."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


class UserRead(BaseModel):
    """Safe response shape — never exposes `password_hash`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    created_at: datetime
