"""
app/schemas/tutor_sch.py
────────────────────────
Pydantic schemas for the Synapse.ai AI tutor endpoints.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ── Input Schemas ─────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    """
    Sent by the frontend when a student highlights text and clicks "AI Explain".
    """
    highlighted_text: str = Field(
        ...,
        min_length=5,
        max_length=4000,
        description="The text the student highlighted in the lesson/quiz.",
    )
    target_language: str = Field(
        "Simple English",
        max_length=50,
        description="Language for the explanation (e.g. 'Hindi', 'Tamil', 'Simple English').",
    )


class AnswerFeedback(BaseModel):
    """
    Sent after a student answers a question following an AI explanation.
    If correct == True and the log hasn't been refunded, award refund coins.
    """
    explanation_log_id: int = Field(
        ..., description="ID from AIExplanationLog.id (returned by /tutor/explain)."
    )
    correct: bool = Field(
        ..., description="True if the student answered the question correctly."
    )


# ── Output Schemas ────────────────────────────────────────────────────────────

class ExplainResponse(BaseModel):
    """
    Returned after a successful AI explanation call.
    """
    explanation_log_id: int
    explanation: str
    cost_coins: int
    new_balance: int
    target_language: str


class FeedbackResponse(BaseModel):
    """
    Returned after processing answer feedback.
    """
    refunded: bool
    coins_returned: int
    new_balance: int
    message: str
