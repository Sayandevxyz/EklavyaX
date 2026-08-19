"""
app/schemas/bounty_sch.py
─────────────────────────
Pydantic schemas for the Teacher Bounty Board feature.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Input Schemas ─────────────────────────────────────────────────────────────

class BountyCreate(BaseModel):
    """Payload for a teacher creating a new bounty."""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    topic: str = Field(..., min_length=2, max_length=100)
    reward_coins: int = Field(..., ge=1, le=10000, description="EduCoins awarded on approval")
    deadline: datetime = Field(..., description="UTC deadline for submissions")


class BountyApproval(BaseModel):
    """Payload for a teacher approving/rejecting a submission."""
    submission_id: int = Field(..., description="ID of the submission to evaluate")
    is_approved: bool = Field(..., description="Approve (True) or reject (False)")
    score: Optional[int] = Field(
        None, ge=0, le=100, description="Score percentage (0-100), optional"
    )


# ── Output Schemas ────────────────────────────────────────────────────────────

class BountyResponse(BaseModel):
    """Bounty data returned to clients."""
    id: int
    teacher_id: int
    title: str
    description: str
    topic: str
    reward_coins: int
    deadline: datetime
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BountySubmissionResponse(BaseModel):
    """Submission data returned to teacher."""
    id: int
    bounty_id: int
    student_id: int
    completed_at: datetime
    is_approved: bool
    score: Optional[int] = None

    model_config = {"from_attributes": True}
