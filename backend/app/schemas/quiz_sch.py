from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field



class QuizStartRequest(BaseModel):
    """Start a new quiz run. Optionally filter by topic."""
    topic: Optional[str] = Field(None, max_length=100, description="Filter questions by topic")
    num_questions: Optional[int] = Field(None, ge=1, le=50, description="Override default quiz size")


class QuizQuestionResponse(BaseModel):
    """A single quiz question served to the client with shuffled options."""
    session_id: int
    quiz_run_id: str
    question_index: int           
    total_questions: int
    prompt: str
    options: List[str]            
    preview_coins: int
    preview_xp: int
    question_shown_at: datetime
    topic: str
    difficulty: str


class QuizStartResponse(BaseModel):
    """Response for starting a quiz – first question."""
    quiz_run_id: str
    total_questions: int
    question: QuizQuestionResponse




class QuizSubmitRequest(BaseModel):
    """Submit an answer for a quiz session question."""
    session_id: int = Field(..., description="QuizSession ID returned by start/next")
    selected_option_index: int = Field(..., ge=0, le=3, description="0-based index into the shuffled options")


class QuizSubmitResponse(BaseModel):
    """Server response after answer submission (correctness from server only)."""
    is_correct: bool
    correct_option_index: int      # In shuffled order, for client feedback
    correct_option_text: Optional[str] = None # Exact text of the correct option
    explanation: Optional[str] = None         # Detailed conceptual explanation
    coins_awarded: int
    xp_awarded: int
    preview_coins: int
    preview_xp: int
    rejection_reason: Optional[str] = None
    detail: Optional[str] = None
    wallet_balance: Optional[int] = None
    wallet_xp: Optional[int] = None
    streak: int                    




class QuizNextResponse(BaseModel):
    """Response with the next question or end-of-quiz marker."""
    finished: bool
    question: Optional[QuizQuestionResponse] = None




class QuizAnswerSummary(BaseModel):
    """Per-question result in the quiz summary."""
    question_index: int
    prompt: str
    is_correct: Optional[bool]
    coins_awarded: int
    xp_awarded: int
    rejection_reason: Optional[str] = None

class QuizSummaryResponse(BaseModel):
    """Post-quiz summary screen data."""
    quiz_run_id: str
    total_questions: int
    answered: int
    correct: int
    accuracy_pct: float
    total_coins: int
    total_xp: int
    rejections: int              
    flags: int                     
    answers: List[QuizAnswerSummary]
    transparency_notices: List[str]  
