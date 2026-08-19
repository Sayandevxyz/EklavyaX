"""
app/api/routes/auth.py
──────────────────────
Authentication endpoints: register, login, and profile.

POST /auth/register  – Create account, assign faction, init wallet/streak
POST /auth/login     – Authenticate, return JWT
GET  /auth/me        – Get current user profile (protected)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_current_user, verify_password, hash_password
from app.db import models
from app.db.database import get_db
from app.schemas.user_sch import (
    PasswordChange,
    StreakResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.game_logic import assign_faction, earn_coins_and_xp, update_streak
from app.core.security import hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── POST /auth/register ───────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user:
    1. Validate unique username/email.
    2. Hash password.
    3. Assign to a faction (smallest faction wins ties randomly).
    4. Initialize Wallet (with starting coins) and Streak.
    5. Return JWT token + user data.
    """
    # Check username uniqueness
    if db.query(models.User).filter_by(username=payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken.",
        )

    # Check email uniqueness
    if db.query(models.User).filter_by(email=payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # Assign faction (teachers and admins don't join factions)
    faction: models.Faction | None = None
    if payload.role == "student":
        faction = assign_faction(db)

    # Resolve default avatar if not explicitly set
    avatar_url = payload.avatar_url
    if not avatar_url:
        is_female = payload.gender in ("female", "girl")
        if payload.role.value == "teacher":
            avatar_url = "assets/img/teacher_female.jpg" if is_female else "assets/img/teacher_male.jpg"
        else:
            avatar_url = "assets/img/student_girl.jpg" if is_female else "assets/img/student_boy.jpg"

    # Create user
    user = models.User(
        username=payload.username,
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        role=models.UserRole(payload.role.value),
        gender=payload.gender,
        avatar_url=avatar_url,
        faction_id=faction.id if faction else None,
    )
    db.add(user)

    try:
        db.flush()  # Get the user.id without committing
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create account due to a conflict. Please try again.",
        )

    # Initialize Wallet with starting coins
    wallet = models.Wallet(
        user_id=user.id,
        balance=settings.NEW_USER_COINS,
        xp=0,
    )
    db.add(wallet)

    # Welcome transaction
    welcome_tx = models.Transaction(
        user_id=user.id,
        amount=settings.NEW_USER_COINS,
        xp_change=0,
        reason="welcome_bonus",
    )
    db.add(welcome_tx)

    # Initialize Streak
    streak = models.Streak(user_id=user.id)
    db.add(streak)

    db.commit()
    db.refresh(user)

    # Issue JWT
    token = create_access_token(subject=user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ── POST /auth/login ──────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with username/email and password",
)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token.
    Accepts either username or email in the `username` field.
    """
    # Try username first, then email
    user = (
        db.query(models.User).filter_by(username=payload.username).first()
        or db.query(models.User).filter_by(email=payload.username).first()
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Auto-resolve avatar_url if missing
    if not user.avatar_url:
        is_female = user.gender in ("female", "girl")
        if user.role == models.UserRole.teacher:
            user.avatar_url = "assets/img/teacher_female.jpg" if is_female else "assets/img/teacher_male.jpg"
        else:
            user.avatar_url = "assets/img/student_girl.jpg" if is_female else "assets/img/student_boy.jpg"
        db.commit()
        db.refresh(user)

    token = create_access_token(subject=user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the profile of the currently authenticated user."""
    if not current_user.avatar_url:
        is_female = current_user.gender in ("female", "girl")
        if current_user.role == models.UserRole.teacher:
            current_user.avatar_url = "assets/img/teacher_female.jpg" if is_female else "assets/img/teacher_male.jpg"
        else:
            current_user.avatar_url = "assets/img/student_girl.jpg" if is_female else "assets/img/student_boy.jpg"
        db.commit()
        db.refresh(current_user)
    return UserResponse.model_validate(current_user)


# ── GET /auth/me/streak ───────────────────────────────────────────────────────

@router.get(
    "/me/streak",
    response_model=StreakResponse,
    summary="Get current user's streak data",
)
def get_my_streak(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the learning streak for the authenticated user."""
    streak = db.query(models.Streak).filter_by(user_id=current_user.id).first()
    if not streak:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Streak not found.")
    return StreakResponse.model_validate(streak)


# ── POST /auth/me/activity ────────────────────────────────────────────────────

@router.post(
    "/me/activity",
    summary="Record learning activity (updates streak and awards daily coins)",
)
def record_activity(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Call this endpoint whenever a student completes a learning activity.
    Updates the streak and awards daily streak bonus coins if it's a new day.
    """
    streak = update_streak(db, current_user.id)

    # Award streak bonus only if streak was just extended (not if already logged today)
    coins_awarded = 0
    xp_awarded = 0
    if streak.last_activity_date is not None:
        # Only award if this is actually a new-day streak update
        coins_awarded = settings.STREAK_BONUS_COINS
        xp_awarded = settings.STREAK_BONUS_XP
        earn_coins_and_xp(
            db,
            current_user.id,
            coins=coins_awarded,
            xp=xp_awarded,
            reason="daily_streak",
        )

    return {
        "message": "Activity recorded!",
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "coins_awarded": coins_awarded,
        "xp_awarded": xp_awarded,
    }


# ── PUT /auth/me ──────────────────────────────────────────────────────────────

@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current authenticated user profile",
)
def update_me(
    payload: UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile details (name, email, avatar, phone, bio, etc.) for the current user."""
    # If username changed, check uniqueness
    if payload.username and payload.username.strip() and payload.username != current_user.username:
        new_username = payload.username.strip()
        existing = (
            db.query(models.User)
            .filter(models.User.username == new_username, models.User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken by another user.",
            )
        current_user.username = new_username

    # If email changed, check uniqueness
    if payload.email and str(payload.email) != current_user.email:
        new_email = str(payload.email).strip().lower()
        existing = (
            db.query(models.User)
            .filter(models.User.email == new_email, models.User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists.",
            )
        current_user.email = new_email

    if payload.gender is not None:
        current_user.gender = payload.gender
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.roll is not None:
        current_user.roll = payload.roll
    if payload.grade is not None:
        current_user.grade = payload.grade
    if payload.school is not None:
        current_user.school = payload.school
    if payload.target_exam is not None:
        current_user.target_exam = payload.target_exam
    if payload.bio is not None:
        current_user.bio = payload.bio

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


# ── POST /auth/change-password ────────────────────────────────────────────────

@router.post(
    "/change-password",
    summary="Change password for the current authenticated user",
)
def change_password(
    payload: PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password verifying the current password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters.",
        )
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}

