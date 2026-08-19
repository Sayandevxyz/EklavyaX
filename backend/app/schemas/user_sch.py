"""
app/schemas/user_sch.py
───────────────────────
Pydantic schemas for User authentication and responses.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


# ── Input Schemas ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Payload for registering a new user."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique display name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Plain-text password (min 8 chars)")
    role: UserRole = Field(UserRole.student, description="User role")
    gender: Optional[str] = Field(None, description="User gender: boy/girl/male/female/other")
    avatar_url: Optional[str] = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, hyphens, underscores.")
        return v.lower()


class UserLogin(BaseModel):
    """Payload for logging in (accepts username OR email in the `username` field)."""
    username: str = Field(..., description="Username or email")
    password: str


class UserUpdate(BaseModel):
    """Payload for updating user profile."""
    username: Optional[str] = Field(None, min_length=2, max_length=50, description="Display name / username")
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    roll: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    target_exam: Optional[str] = None
    bio: Optional[str] = None


class PasswordChange(BaseModel):
    """Payload for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=6, description="New password (min 6 chars)")


# ── Output Schemas ────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Safe user representation returned from all endpoints."""
    id: int
    username: str
    email: str
    role: UserRole
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    roll: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    target_exam: Optional[str] = None
    bio: Optional[str] = None
    faction_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT auth response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class StreakResponse(BaseModel):
    """Streak data for the current user."""
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[str] = None
    streak_freezes: int

    model_config = {"from_attributes": True}
