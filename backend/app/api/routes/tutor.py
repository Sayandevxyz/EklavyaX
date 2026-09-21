from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
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
from app.services.ai_service import get_explanation, get_visual_explanation, transcribe_audio_groq
from app.services.game_logic import earn_coins_and_xp, refund_coins, spend_coins

router = APIRouter(prefix="/tutor", tags=["GRAVITY.ai Tutor"])


@router.post("/visual-explain", response_model=ExplainResponse, summary="Analyze a student visual doubt")
async def explain_visual(
    file: UploadFile = File(...),
    instruction: str = Form("Solve this visual doubt step-by-step."),
    target_language: str = Form("English"),
    current_user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    content_type = file.content_type or "image/jpeg"
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG, or WebP image.")
    image_bytes = await file.read()
    if not image_bytes or len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be between 1 byte and 10MB.")

    cost = settings.AI_EXPLAIN_COST
    wallet = db.query(models.Wallet).filter_by(user_id=current_user.id).first()
    if not wallet or wallet.balance < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient EduCoins. Visual AI costs {cost} coins.")
    updated_wallet = spend_coins(db, current_user.id, coins=cost, reason="ai_visual_explain")
    explanation = await get_visual_explanation(image_bytes, content_type, instruction, target_language)
    log_entry = models.AIExplanationLog(
        user_id=current_user.id,
        highlighted_text=f"Visual doubt: {instruction}",
        target_language=target_language,
        explanation=explanation,
        cost_coins=cost,
        refunded=False,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return ExplainResponse(
        explanation_log_id=log_entry.id,
        explanation=explanation,
        cost_coins=cost,
        new_balance=updated_wallet.balance,
        target_language=target_language,
    )



@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="GRAVITY.ai: Get an AI explanation for highlighted text",
)
async def explain_text(
    payload: ExplainRequest,
    current_user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
 
    cost = settings.AI_EXPLAIN_COST

 
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


    updated_wallet = spend_coins(
        db, current_user.id, coins=cost, reason="ai_explain"
    )

   
    if settings.AI_PROVIDER.lower() == "groq":
        key_loaded = bool(settings.GROQ_API_KEY)
        active_model = settings.GROQ_MODEL
    elif settings.AI_PROVIDER.lower() == "openrouter":
        key_loaded = bool(settings.OPENROUTER_API_KEY)
        active_model = settings.OPENROUTER_MODEL
    elif settings.AI_PROVIDER.lower() == "gemini":
        key_loaded = bool(settings.GEMINI_API_KEY)
        active_model = settings.GEMINI_MODEL
    else:
        key_loaded = bool(settings.OPENAI_API_KEY)
        active_model = settings.OPENAI_MODEL
    print(
        f"DEBUG AI: provider={settings.AI_PROVIDER}, "
        f"key_loaded={key_loaded}, "
        f"model={active_model}"
    )

    explanation_text = await get_explanation(
        highlighted_text=payload.highlighted_text,
        target_language=payload.target_language,
    )

    
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

   
    return ExplainResponse(
        explanation_log_id=log_entry.id,
        explanation=explanation_text,
        cost_coins=cost,
        new_balance=updated_wallet.balance,
        target_language=payload.target_language,
    )




@router.post(
    "/answer-feedback",
    response_model=FeedbackResponse,
    summary="GRAVITY.ai: Record answer feedback – refund coins on correct answer",
)
def answer_feedback(
    payload: AnswerFeedback,
    current_user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
   
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


    refund_amount = settings.AI_REFUND_COINS
    updated_wallet = refund_coins(
        db,
        current_user.id,
        coins=refund_amount,
        reason="ai_explain_good_student_refund",
    )

   
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




@router.post(
    "/transcribe",
    summary="GRAVITY.ai: Transcribe voice audio via Groq Cloud Whisper AI",
)
async def transcribe_voice(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
):
    """
    Transcribe spoken question audio using Groq Cloud Whisper API (whisper-large-v3).
    Supports English, Hindi, Tamil, and other regional languages.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio data received.",
        )

    transcription = await transcribe_audio_groq(
        audio_bytes=audio_bytes,
        filename=file.filename or "recording.webm",
        language=language,
    )
    return {"text": transcription}


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

