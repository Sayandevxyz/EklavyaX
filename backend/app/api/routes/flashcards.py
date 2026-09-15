from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/flashcards", tags=["Spaced Repetition Flashcards"])


class ReviewSubmission(BaseModel):
    card_id: int
    rating: int  # 1: Again (failed), 2: Hard, 3: Good, 4: Easy


class FlashcardCreate(BaseModel):
    topic: str
    front: str
    back: str


def calculate_sm2(repetition: int, interval: int, ease_factor: float, rating: int):
    """
    SuperMemo-2 (SM-2) spaced repetition interval calculator.
    rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    """
    if rating < 3:
        # Failed or need immediate review
        repetition = 0
        interval = 1
    else:
        if repetition == 0:
            interval = 1
        elif repetition == 1:
            interval = 3 if rating == 3 else 6
        else:
            interval = int(interval * ease_factor)
        repetition += 1

    # Update ease factor
    # Quality scale in SM2 is 0-5. Here mapping: 1->2, 2->3, 3->4, 4->5
    quality = rating + 1
    ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if ease_factor < 1.3:
        ease_factor = 1.3

    return repetition, interval, round(ease_factor, 2)


@router.get("/due", summary="Get flashcards due for revision today")
def get_due_flashcards(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all flashcards due on or before today."""
    today = datetime.now(timezone.utc).date()

    cards = (
        db.query(models.Flashcard)
        .filter(models.Flashcard.user_id == current_user.id, models.Flashcard.due_date <= today)
        .order_by(models.Flashcard.due_date.asc())
        .all()
    )

    total_cards = db.query(models.Flashcard).filter_by(user_id=current_user.id).count()

    return {
        "today": today.isoformat(),
        "due_count": len(cards),
        "total_cards": total_cards,
        "cards": [
            {
                "id": c.id,
                "topic": c.topic,
                "front": c.front,
                "back": c.back,
                "interval_days": c.interval_days,
                "repetition_count": c.repetition_count,
                "due_date": c.due_date.isoformat(),
            }
            for c in cards
        ],
    }


@router.post("/review", summary="Submit a flashcard review rating")
def review_flashcard(
    payload: ReviewSubmission,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Updates the flashcard's ease factor, interval, and next due date using SM-2."""
    card = (
        db.query(models.Flashcard)
        .filter_by(id=payload.card_id, user_id=current_user.id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")

    new_rep, new_interval, new_ef = calculate_sm2(
        card.repetition_count,
        card.interval_days,
        card.ease_factor,
        payload.rating,
    )

    card.repetition_count = new_rep
    card.interval_days = new_interval
    card.ease_factor = new_ef
    card.due_date = datetime.now(timezone.utc).date() + timedelta(days=new_interval)

    # Award a small XP bonus for daily spaced repetition practice
    if current_user.wallet and payload.rating >= 3:
        current_user.wallet.xp += 5

    db.commit()

    return {
        "status": "reviewed",
        "card_id": card.id,
        "next_due_date": card.due_date.isoformat(),
        "interval_days": new_interval,
        "repetition_count": new_rep,
    }


@router.post("/sync-mistakes", summary="Auto-generate flashcards from quiz mistakes")
def sync_quiz_mistakes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Scans the user's incorrect quiz responses and creates spaced repetition cards
    so students can review and master concepts they previously struggled with.
    """
    wrong_sessions = (
        db.query(models.QuizSession)
        .filter_by(user_id=current_user.id, is_correct=False)
        .all()
    )

    cards_created = 0
    today = datetime.now(timezone.utc).date()

    for s in wrong_sessions:
        q = s.question
        if not q:
            continue

        # Check if card already exists for this question
        exists = (
            db.query(models.Flashcard)
            .filter_by(user_id=current_user.id, source_question_id=q.id)
            .first()
        )
        if exists:
            continue

        options = q.get_canonical_options()
        correct_answer_text = (
            options[q.correct_option_index]
            if 0 <= q.correct_option_index < len(options)
            else "Option " + str(q.correct_option_index + 1)
        )

        back_content = f"**Correct Answer:** {correct_answer_text}\n\n"
        if q.explanation:
            back_content += f"**Explanation:**\n{q.explanation}"
        else:
            back_content += "Revise the core formula and definitions related to this concept."

        card = models.Flashcard(
            user_id=current_user.id,
            topic=q.topic,
            front=q.prompt,
            back=back_content,
            source_question_id=q.id,
            interval_days=1,
            ease_factor=2.5,
            repetition_count=0,
            due_date=today,
        )
        db.add(card)
        cards_created += 1

    db.commit()

    return {
        "status": "synced",
        "new_cards_created": cards_created,
        "message": f"{cards_created} naye flashcards aapki galtiyon se create kiye gaye hain!",
    }


@router.post("/custom", summary="Create a custom user flashcard")
def create_custom_card(
    payload: FlashcardCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Manually add a flashcard."""
    today = datetime.now(timezone.utc).date()
    card = models.Flashcard(
        user_id=current_user.id,
        topic=payload.topic,
        front=payload.front,
        back=payload.back,
        interval_days=1,
        ease_factor=2.5,
        repetition_count=0,
        due_date=today,
    )
    db.add(card)
    db.commit()

    return {"status": "created", "card_id": card.id}
