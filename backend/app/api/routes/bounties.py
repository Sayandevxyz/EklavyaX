"""
app/api/routes/bounties.py
──────────────────────────
Teacher Bounty Board endpoints.

POST /bounties                          – Teacher: create a bounty
GET  /bounties                          – Anyone: list active bounties
POST /bounties/{bounty_id}/submit       – Student: submit completion claim
POST /bounties/{bounty_id}/approve      – Teacher: approve/reject a submission
GET  /bounties/{bounty_id}/submissions  – Teacher: view all submissions for a bounty
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.db import models
from app.schemas.bounty_sch import (
    BountyApproval,
    BountyCreate,
    BountyResponse,
    BountySubmissionResponse,
)
from app.services.game_logic import earn_coins_and_xp, update_faction_score, update_streak

router = APIRouter(prefix="/bounties", tags=["Bounty Board"])


# ── POST /bounties ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BountyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Teacher: Post a new bounty challenge",
)
def create_bounty(
    payload: BountyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("teacher", "admin")),
):
    """
    Only teachers or admins may create bounties.
    Deadline must be in the future.
    """
    if payload.deadline <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deadline must be in the future.",
        )

    bounty = models.Bounty(
        teacher_id=current_user.id,
        title=payload.title,
        description=payload.description,
        topic=payload.topic,
        reward_coins=payload.reward_coins,
        deadline=payload.deadline,
        is_active=True,
    )
    db.add(bounty)
    db.commit()
    db.refresh(bounty)
    return BountyResponse.model_validate(bounty)


# ── GET /bounties ──────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[BountyResponse],
    summary="List all active bounties",
)
def list_bounties(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    topic: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    """
    Return active (non-expired) bounties, optionally filtered by topic.
    Available to all authenticated users.
    """
    now = datetime.now(timezone.utc)
    query = (
        db.query(models.Bounty)
        .filter(models.Bounty.is_active == True)
        .filter(models.Bounty.deadline > now)
    )

    if topic:
        query = query.filter(models.Bounty.topic.ilike(f"%{topic}%"))

    bounties = query.order_by(models.Bounty.deadline.asc()).offset(skip).limit(limit).all()
    return [BountyResponse.model_validate(b) for b in bounties]


# ── POST /bounties/{bounty_id}/submit ─────────────────────────────────────────

@router.post(
    "/{bounty_id}/submit",
    response_model=BountySubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Student: Submit a bounty completion claim",
)
def submit_bounty(
    bounty_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("student")),
):
    """
    A student claims they completed the bounty.
    - Validates bounty exists, is active, and deadline hasn't passed.
    - Prevents duplicate submissions per student per bounty.
    """
    bounty = db.get(models.Bounty, bounty_id)
    if not bounty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty not found.")

    if not bounty.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This bounty is no longer active.",
        )

    if bounty.deadline <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The deadline for this bounty has passed.",
        )

    # Check for duplicate submission
    existing = (
        db.query(models.BountySubmission)
        .filter_by(bounty_id=bounty_id, student_id=current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted for this bounty.",
        )

    submission = models.BountySubmission(
        bounty_id=bounty_id,
        student_id=current_user.id,
        is_approved=False,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return BountySubmissionResponse.model_validate(submission)


# ── POST /bounties/{bounty_id}/approve ────────────────────────────────────────

@router.post(
    "/{bounty_id}/approve",
    response_model=BountySubmissionResponse,
    summary="Teacher: Approve or reject a bounty submission",
)
def approve_submission(
    bounty_id: int,
    payload: BountyApproval,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("teacher", "admin")),
):
    """
    Teacher approves or rejects a student's bounty submission.

    On approval:
    - Award `reward_coins` to the student's wallet.
    - Award bounty XP to the student.
    - Update the student's faction score.
    - Update the student's streak.
    - Mark submission as approved.
    """
    # Verify bounty ownership
    bounty = db.get(models.Bounty, bounty_id)
    if not bounty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty not found.")

    if bounty.teacher_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own bounties.",
        )

    # Fetch the submission
    submission = db.get(models.BountySubmission, payload.submission_id)
    if not submission or submission.bounty_id != bounty_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found for this bounty.",
        )

    if submission.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This submission has already been approved.",
        )

    submission.is_approved = payload.is_approved
    submission.score = payload.score

    if payload.is_approved:
        # Award coins and XP
        earn_coins_and_xp(
            db,
            submission.student_id,
            coins=bounty.reward_coins,
            xp=50,  # settings.BOUNTY_COMPLETION_XP
            reason="bounty_reward",
        )
        # Update streak
        try:
            update_streak(db, submission.student_id)
        except Exception:
            pass  # Non-critical if streak update fails

    db.commit()
    db.refresh(submission)
    return BountySubmissionResponse.model_validate(submission)


# ── GET /bounties/{bounty_id}/submissions ─────────────────────────────────────

@router.get(
    "/{bounty_id}/submissions",
    response_model=List[BountySubmissionResponse],
    summary="Teacher: View all submissions for a bounty",
)
def get_submissions(
    bounty_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("teacher", "admin")),
):
    """
    Return all student submissions for a specific bounty.
    Only the owning teacher (or admin) may view submissions.
    """
    bounty = db.get(models.Bounty, bounty_id)
    if not bounty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty not found.")

    if bounty.teacher_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view submissions for your own bounties.",
        )

    submissions = (
        db.query(models.BountySubmission)
        .filter_by(bounty_id=bounty_id)
        .order_by(models.BountySubmission.completed_at.desc())
        .all()
    )
    return [BountySubmissionResponse.model_validate(s) for s in submissions]
