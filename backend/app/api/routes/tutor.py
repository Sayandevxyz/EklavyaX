"""
app/api/routes/tutor.py
───────────────────────
Synapse.ai – the AI Explanation microservice endpoints.

POST /tutor/explain         – Highlight + explain (costs EduCoins)
POST /tutor/answer-feedback – Correct answer refunds coins ("Good Student" mechanic)
GET  /tutor/history         – View AI explanation history for current user
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.db import models
from app.schemas.tutor_sch import (
    AnswerFeedback,
    ExplainRequest,
    ExplainResponse,
    FeedbackResponse,
)
from app.services.ai_service import get_explanation
from app.services.game_logic import earn_coins_and_xp, refund_coins, spend_coins

router = APIRouter(prefix="/tutor", tags=["Synapse.ai Tutor"])


# ── POST /tutor/explain ────────────────────────────────────────────────────────

@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Synapse.ai: Get an AI explanation for highlighted text",
)
async def explain_text(
    payload: ExplainRequest,
    current_user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    The core Synapse.ai feature.

    Flow:
    1. Check student has enough EduCoins (AI_EXPLAIN_COST).
    2. Deduct the coins before calling the AI (prevents free-riding).
    3. Call the AI provider (Gemini or OpenAI) with the engineered prompt.
    4. Store the log (for potential refund later).
    5. Return explanation + new balance.
    """
    cost = settings.AI_EXPLAIN_COST

    # 1. Pre-flight balance check
    wallet = db.query(models.Wallet).filter_by(user_id=current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found. Please contact support.",
        )

    if wallet.balance < cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient EduCoins. The AI Explain feature costs {cost} coins. "
                f"Your balance: {wallet.balance} coins."
            ),
        )

    # 2. Deduct coins
    updated_wallet = spend_coins(
        db, current_user.id, coins=cost, reason="ai_explain"
    )

    # 3. Call the AI (async – non-blocking)
    key_loaded = (
        bool(settings.OPENROUTER_API_KEY)
        if settings.AI_PROVIDER.lower() == "openrouter"
        else (
            bool(settings.GEMINI_API_KEY)
            if settings.AI_PROVIDER.lower() == "gemini"
            else bool(settings.OPENAI_API_KEY)
        )
    )
    active_model = (
        settings.OPENROUTER_MODEL
        if settings.AI_PROVIDER.lower() == "openrouter"
        else (
            settings.GEMINI_MODEL
            if settings.AI_PROVIDER.lower() == "gemini"
            else settings.OPENAI_MODEL
        )
    )
    print(
        f"DEBUG AI: provider={settings.AI_PROVIDER}, "
        f"key_loaded={key_loaded}, "
        f"model={active_model}"
    )

    explanation_text = await get_explanation(
        highlighted_text=payload.highlighted_text,
        target_language=payload.target_language,
    )

    # 4. Log the interaction
    log_entry = models.AIExplanationLog(
        user_id=current_user.id,
        highlighted_text=payload.highlighted_text,
        target_language=payload.target_language,
        explanation=explanation_text,
        cost_coins=cost,
        refunded=False,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # 5. Return response
    return ExplainResponse(
        explanation_log_id=log_entry.id,
        explanation=explanation_text,
        cost_coins=cost,
        new_balance=updated_wallet.balance,
        target_language=payload.target_language,
    )


# ── POST /tutor/answer-feedback ────────────────────────────────────────────────

@router.post(
    "/answer-feedback",
    response_model=FeedbackResponse,
    summary="Synapse.ai: Record answer feedback – refund coins on correct answer",
)
def answer_feedback(
    payload: AnswerFeedback,
    current_user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    The 'Good Student' refund mechanic.

    If a student correctly answers the question after using the AI explanation,
    they get a partial refund (AI_REFUND_COINS) as a reward for genuine learning.

    Prevents double-refunds by checking log.refunded flag.
    """
    log_entry = db.get(models.AIExplanationLog, payload.explanation_log_id)

    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI explanation log entry not found.",
        )

    if log_entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This explanation log does not belong to you.",
        )

    # If answer was wrong or log already refunded
    if not payload.correct:
        return FeedbackResponse(
            refunded=False,
            coins_returned=0,
            new_balance=db.query(models.Wallet).filter_by(user_id=current_user.id).first().balance,
            message="Better luck next time! Keep studying and try again.",
        )

    if log_entry.refunded:
        wallet = db.query(models.Wallet).filter_by(user_id=current_user.id).first()
        return FeedbackResponse(
            refunded=False,
            coins_returned=0,
            new_balance=wallet.balance if wallet else 0,
            message="Refund already applied for this explanation.",
        )

    # Apply refund
    refund_amount = settings.AI_REFUND_COINS
    updated_wallet = refund_coins(
        db,
        current_user.id,
        coins=refund_amount,
        reason="ai_explain_good_student_refund",
    )

    # Mark as refunded
    log_entry.refunded = True
    db.commit()

    return FeedbackResponse(
        refunded=True,
        coins_returned=refund_amount,
        new_balance=updated_wallet.balance,
        message=(
            f"🎉 Great work! You understood the concept and answered correctly. "
            f"{refund_amount} EduCoins refunded!"
        ),
    )


# ── GET /tutor/history ────────────────────────────────────────────────────────

@router.get(
    "/history",
    summary="Get current user's AI explanation history",
)
def get_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """Returns the AI explanation log for the authenticated user."""
    logs = (
        db.query(models.AIExplanationLog)
        .filter_by(user_id=current_user.id)
        .order_by(models.AIExplanationLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "highlighted_text": log.highlighted_text[:200] + "..."
            if len(log.highlighted_text) > 200
            else log.highlighted_text,
            "target_language": log.target_language,
            "cost_coins": log.cost_coins,
            "refunded": log.refunded,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


# ── DELETE /tutor/history ─────────────────────────────────────────────────────

@router.delete(
    "/history",
    summary="Clear all AI explanation history for the current user",
)
def clear_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all AI explanation log entries for the authenticated user."""
    deleted_count = (
        db.query(models.AIExplanationLog)
        .filter_by(user_id=current_user.id)
        .delete()
    )
    db.commit()
    return {"deleted": deleted_count, "message": "Explanation history cleared."}

