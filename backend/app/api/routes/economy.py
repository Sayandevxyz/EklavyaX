"""
app/api/routes/economy.py
─────────────────────────
Virtual economy, wallet, challenges, and leaderboard endpoints.

GET  /economy/wallet                – Current user's wallet
GET  /economy/transactions          – Current user's transaction history
POST /economy/earn                  – Earn coins/XP (internal/admin)
POST /economy/spend                 – Spend coins (internal/admin)
POST /challenges                    – Create a peer challenge
POST /challenges/{id}/accept        – Opponent accepts a challenge
POST /challenges/{id}/submit        – Submit challenge result + determine winner
GET  /challenges                    – List current user's challenges
GET  /leaderboard/class             – Top 10 by XP
GET  /leaderboard/faction           – Faction standings
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.db import models
from app.schemas.economy_sch import (
    ChallengeCreate,
    ChallengeResponse,
    ChallengeSubmitResult,
    ClassLeaderboardResponse,
    EarnRequest,
    FactionLeaderboardResponse,
    LeaderboardEntry,
    FactionLeaderboardEntry,
    SpendRequest,
    TransactionResponse,
    WalletResponse,
)
from app.services.game_logic import (
    earn_coins_and_xp,
    get_class_leaderboard,
    get_faction_leaderboard,
    process_challenge_winner,
    spend_coins,
)

router = APIRouter(tags=["Economy & Challenges"])


# ── Wallet ────────────────────────────────────────────────────────────────────

@router.get(
    "/economy/wallet",
    response_model=WalletResponse,
    summary="Get current user's wallet (EduCoins + XP)",
)
def get_wallet(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = db.query(models.Wallet).filter_by(user_id=current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found.")
    return WalletResponse.model_validate(wallet)


@router.get(
    "/economy/transactions",
    response_model=List[TransactionResponse],
    summary="Get current user's transaction history",
)
def get_transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    """Returns the last `limit` transactions for the authenticated user."""
    txs = (
        db.query(models.Transaction)
        .filter_by(user_id=current_user.id)
        .order_by(models.Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [TransactionResponse.model_validate(t) for t in txs]


# ── Internal earn / spend ─────────────────────────────────────────────────────

@router.post(
    "/economy/earn",
    response_model=WalletResponse,
    summary="[Admin] Award coins and/or XP to current user",
)
def earn(
    payload: EarnRequest,
    current_user: models.User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    """
    Admin/teacher endpoint to manually award coins and XP.
    Used internally by other services and for testing.
    """
    wallet = earn_coins_and_xp(
        db, current_user.id, coins=payload.coins, xp=payload.xp, reason=payload.reason
    )
    return WalletResponse.model_validate(wallet)


@router.post(
    "/economy/claim-reward",
    response_model=WalletResponse,
    summary="Award earned coins and XP to authenticated user upon task/activity completion",
)
def claim_reward(
    payload: EarnRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows authenticated students/teachers to claim earned coins and XP
    from completing assignments, interactive simulations, and quizzes.
    """
    coins = min(payload.coins, 100)
    xp = min(payload.xp, 100)
    wallet = earn_coins_and_xp(
        db, current_user.id, coins=coins, xp=xp, reason=payload.reason
    )
    return WalletResponse.model_validate(wallet)



@router.post(
    "/economy/spend",
    response_model=WalletResponse,
    summary="[Internal] Deduct coins from current user's wallet",
)
def spend(
    payload: SpendRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deduct coins from the authenticated user's wallet.
    Raises 400 if balance is insufficient.
    """
    wallet = spend_coins(db, current_user.id, coins=payload.coins, reason=payload.reason)
    return WalletResponse.model_validate(wallet)


# ── Challenges ────────────────────────────────────────────────────────────────

@router.post(
    "/challenges",
    response_model=ChallengeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Student: Create a new peer challenge",
)
def create_challenge(
    payload: ChallengeCreate,
    current_user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    Create a 1v1 challenge with an optional EduCoin wager.
    Wager is deducted immediately from the challenger's wallet.
    """
    # Validate wager against wallet
    if payload.wager_coins > 0:
        wallet = db.query(models.Wallet).filter_by(user_id=current_user.id).first()
        if not wallet or wallet.balance < payload.wager_coins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance to wager {payload.wager_coins} EduCoins.",
            )
        spend_coins(db, current_user.id, coins=payload.wager_coins, reason="challenge_wager")

    # Validate opponent exists
    if payload.opponent_id is not None:
        opponent = db.get(models.User, payload.opponent_id)
        if not opponent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opponent with id {payload.opponent_id} not found.",
            )
        if opponent.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot challenge yourself.",
            )

    challenge = models.Challenge(
        challenger_id=current_user.id,
        opponent_id=payload.opponent_id,
        topic=payload.topic,
        wager_coins=payload.wager_coins,
        status=models.ChallengeStatus.pending,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return ChallengeResponse.model_validate(challenge)


@router.post(
    "/challenges/{challenge_id}/accept",
    response_model=ChallengeResponse,
    summary="Student: Accept a pending challenge",
)
def accept_challenge(
    challenge_id: int,
    current_user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    Accept a pending challenge.
    Deducts the wager from the opponent's wallet if wager > 0.
    """
    challenge = db.get(models.Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")

    if challenge.status != models.ChallengeStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Challenge is already in '{challenge.status.value}' status.",
        )

    # Validate this user is the correct opponent (or challenge is open)
    if challenge.opponent_id is not None and challenge.opponent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This challenge was not issued to you.",
        )

    if challenge.challenger_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot accept your own challenge.",
        )

    # For open challenges, assign this user as the opponent
    if challenge.opponent_id is None:
        challenge.opponent_id = current_user.id

    # Deduct opponent's wager
    if challenge.wager_coins > 0:
        spend_coins(
            db, current_user.id, coins=challenge.wager_coins, reason="challenge_wager"
        )

    challenge.status = models.ChallengeStatus.accepted
    db.commit()
    db.refresh(challenge)
    return ChallengeResponse.model_validate(challenge)


@router.post(
    "/challenges/{challenge_id}/submit",
    response_model=ChallengeResponse,
    summary="Submit challenge result and determine winner",
)
def submit_challenge_result(
    challenge_id: int,
    payload: ChallengeSubmitResult,
    current_user: models.User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    """
    Record the winner of a challenge.
    Transfers the wager pot (both sides combined) to the winner.
    Awards bonus XP.

    In MVP, this is called by the quiz system once both players finish.
    """
    challenge = db.get(models.Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")

    # Only participants can submit results (or admin)
    if current_user.role != models.UserRole.admin and current_user.id not in {
        challenge.challenger_id, challenge.opponent_id
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only challenge participants can submit results.",
        )

    updated_challenge, _ = process_challenge_winner(db, challenge_id, payload.winner_id)
    return ChallengeResponse.model_validate(updated_challenge)


@router.get(
    "/challenges",
    response_model=List[ChallengeResponse],
    summary="List all challenges involving current user",
)
def list_challenges(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: str | None = None,
):
    """Return all challenges where the current user is challenger or opponent."""
    query = db.query(models.Challenge).filter(
        or_(
            models.Challenge.challenger_id == current_user.id,
            models.Challenge.opponent_id == current_user.id,
        )
    )

    if status_filter:
        try:
            status_enum = models.ChallengeStatus(status_filter)
            query = query.filter(models.Challenge.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Choices: pending, accepted, completed, cancelled",
            )

    challenges = query.order_by(models.Challenge.created_at.desc()).all()
    return [ChallengeResponse.model_validate(c) for c in challenges]


# ── Leaderboards ──────────────────────────────────────────────────────────────

@router.get(
    "/leaderboard/class",
    response_model=ClassLeaderboardResponse,
    summary="Top 10 students by XP",
)
def class_leaderboard(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the top 10 students ranked by XP.
    Uses Redis cache if available; otherwise queries the DB directly.
    """
    entries_raw = get_class_leaderboard(db, limit=10)
    entries = [LeaderboardEntry(**e) for e in entries_raw]
    return ClassLeaderboardResponse(entries=entries)


@router.get(
    "/leaderboard/faction",
    response_model=FactionLeaderboardResponse,
    summary="Faction war standings",
)
def faction_leaderboard(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all factions ranked by their aggregate score."""
    entries_raw = get_faction_leaderboard(db)
    entries = [FactionLeaderboardEntry(**e) for e in entries_raw]
    return FactionLeaderboardResponse(entries=entries)
