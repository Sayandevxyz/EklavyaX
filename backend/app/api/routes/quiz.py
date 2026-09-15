from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user, require_role
from app.db import models
from app.db.database import get_db
from app.services.ai_service import sanitize_latex_to_unicode
from app.schemas.quiz_sch import (
    QuizAnswerSummary,
    QuizNextResponse,
    QuizQuestionResponse,
    QuizStartRequest,
    QuizStartResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizSummaryResponse,
)
from app.services.safeguards import (
    generate_shuffled_options,
    grant_safeguarded_reward,
    permutation_to_str,
    str_to_permutation,
)

router = APIRouter(prefix="/quiz", tags=["Quiz"])



@router.post(
    "/generate-ai",
    summary="Generate new STEM questions on-the-fly using AI and add to question bank",
)
async def generate_ai_quiz(
    topic: str = "Physics",
    num_questions: int = 5,
    current_user: models.User = Depends(require_role("student", "teacher", "admin")),
    db: Session = Depends(get_db),
):
    
    from app.services.ai_service import generate_ai_quiz_questions

    generated = await generate_ai_quiz_questions(topic=topic, num_questions=num_questions)
    saved_questions = []

    for q_data in generated:
        q = models.QuizQuestion(**q_data)
        db.add(q)
        saved_questions.append(q)

    db.commit()
    return {
        "success": True,
        "message": f"Successfully generated {len(saved_questions)} new AI questions for topic '{topic}'.",
        "count": len(saved_questions),
    }



def _run_async(coro):
    import asyncio
    import concurrent.futures
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=12)
    else:
        return asyncio.run(coro)


@router.post(
    "/start",
    response_model=QuizStartResponse,
    summary="Start a new quiz run with fresh dynamic questions from Groq AI",
)
def start_quiz(
    payload: QuizStartRequest,
    current_user: models.User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    """
    Initiates a new quiz run with exactly 10 questions.
    1. Generates 10 fresh, unique questions via Groq Cloud AI.
    2. Falls back to randomly sampled question bank if Groq is offline or throttling.
    3. Shuffles answer options per session and server stamps question_shown_at.
    """
    num_q = payload.num_questions or 10  # Enforce 10 questions per quiz run (or test override)
    target_topic = payload.topic if payload.topic else random.choice(["Physics", "Chemistry", "Mathematics", "Biology", "Computer Science"])

    selected_questions: List[models.QuizQuestion] = []

    # 1. Attempt dynamic question generation via Groq Cloud AI
    try:
        from app.services.ai_service import generate_ai_quiz_questions
        ai_questions = _run_async(generate_ai_quiz_questions(topic=target_topic, num_questions=num_q))
        if ai_questions:
            for q_data in ai_questions:
                q = models.QuizQuestion(**q_data)
                db.add(q)
                selected_questions.append(q)
            db.commit()
            for q in selected_questions:
                db.refresh(q)
    except Exception as exc:
        # Fallback cleanly to database question bank
        pass

    # 2. Fallback to existing question bank if AI generation didn't yield full set
    if len(selected_questions) < num_q:
        from app.services.game_logic import ensure_quiz_questions_exist
        ensure_quiz_questions_exist(db)

        query = db.query(models.QuizQuestion)
        if payload.topic:
            filtered = query.filter(models.QuizQuestion.topic.ilike(f"%{payload.topic}%")).all()
            pool = filtered if filtered else query.all()
        else:
            pool = query.all()

        if pool:
            needed = num_q - len(selected_questions)
            # Pick random distinct questions not already in selected_questions
            existing_ids = {q.id for q in selected_questions if q.id}
            available = [q for q in pool if q.id not in existing_ids]
            if not available:
                available = pool
            sample_size = min(needed, len(available))
            fallback_sample = random.sample(available, sample_size)
            selected_questions.extend(fallback_sample)

    if not selected_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No quiz questions available. Please try again.",
        )

    num_q = len(selected_questions)
    quiz_run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    sessions: List[models.QuizSession] = []
    first_shuffled_options: List[str] = []

    for idx, q in enumerate(selected_questions):
        shuffled_options, permutation = generate_shuffled_options(q)
        q_session = models.QuizSession(
            quiz_run_id=quiz_run_id,
            user_id=current_user.id,
            question_id=q.id,
            question_index=idx,
            total_questions=num_q,
            shuffled_order=permutation_to_str(permutation),
            question_shown_at=now if idx == 0 else now,  
        )
        db.add(q_session)
        sessions.append(q_session)
        if idx == 0:
            first_shuffled_options = shuffled_options

    db.commit()
    db.refresh(sessions[0])

    q0 = selected_questions[0]
    first_q_response = QuizQuestionResponse(
        session_id=sessions[0].id,
        quiz_run_id=quiz_run_id,
        question_index=0,
        total_questions=num_q,
        prompt=sanitize_latex_to_unicode(q0.prompt),
        options=[sanitize_latex_to_unicode(o) for o in first_shuffled_options],
        preview_coins=q0.preview_coins,
        preview_xp=q0.preview_xp,
        question_shown_at=sessions[0].question_shown_at,
        topic=q0.topic,
        difficulty=q0.difficulty,
    )

    return QuizStartResponse(
        quiz_run_id=quiz_run_id,
        total_questions=num_q,
        question=first_q_response,
    )



@router.post(
    "/submit",
    response_model=QuizSubmitResponse,
    summary="Submit an answer — validated strictly via Part A safeguards",
)
def submit_answer(
    payload: QuizSubmitRequest,
    current_user: models.User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    """
    Submits an answer to a question session.
    Gated strictly through server-side safeguards:
      1. Server answer validation
      2. Minimum cooldown check (server-recorded timestamp)
      3. Daily earn caps (reduced/reject/zero policy)
      4. Reward grant + audit log
      5. Pattern anomaly check
    """
    session = db.get(models.QuizSession, payload.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz session not found.",
        )

    if session.user_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This quiz session does not belong to you.",
        )

    if session.submitted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This question has already been answered.",
        )

   
    result = grant_safeguarded_reward(
        db=db,
        user_id=current_user.id,
        session=session,
        selected_shuffled_index=payload.selected_option_index,
    )

    
    run_sessions = (
        db.query(models.QuizSession)
        .filter_by(quiz_run_id=session.quiz_run_id)
        .order_by(models.QuizSession.question_index.asc())
        .all()
    )
    streak = 0
    for s in run_sessions:
        if s.submitted_at:
            if s.is_correct:
                streak += 1
            else:
                streak = 0

    # Determine correct option index in the shuffled list and resolve explanation
    perm = str_to_permutation(session.shuffled_order)
    canonical_correct = session.question.correct_option_index
    shuffled_correct_index = perm.index(canonical_correct) if canonical_correct in perm else 0
    canonical_options = session.question.get_canonical_options()
    correct_option_text = canonical_options[canonical_correct] if 0 <= canonical_correct < len(canonical_options) else ""
    correct_option_text = sanitize_latex_to_unicode(correct_option_text)

    explanation = session.question.explanation
    if not explanation:
        explanation = f"The correct answer is '{correct_option_text}'."
    explanation = sanitize_latex_to_unicode(explanation)

    wallet = db.query(models.Wallet).filter_by(user_id=current_user.id).first()

    return QuizSubmitResponse(
        is_correct=result["is_correct"],
        correct_option_index=shuffled_correct_index,
        correct_option_text=correct_option_text,
        explanation=explanation,
        coins_awarded=result["coins_awarded"],
        xp_awarded=result["xp_awarded"],
        preview_coins=session.question.preview_coins,
        preview_xp=session.question.preview_xp,
        rejection_reason=result.get("rejection_reason"),
        detail=result.get("detail"),
        wallet_balance=wallet.balance if wallet else None,
        wallet_xp=wallet.xp if wallet else None,
        streak=streak,
    )



@router.get(
    "/{quiz_run_id}/next/{question_index}",
    response_model=QuizNextResponse,
    summary="Get the next question in the current quiz run",
)
def get_next_question(
    quiz_run_id: str,
    question_index: int,
    current_user: models.User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    """
    Fetches the question at `question_index` for this run.
    Stamps `question_shown_at` at retrieval time to ensure accurate cooldown timing.
    """
    session = (
        db.query(models.QuizSession)
        .filter_by(quiz_run_id=quiz_run_id, question_index=question_index)
        .first()
    )

    if not session:
        return QuizNextResponse(finished=True, question=None)

    if session.user_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


    now = datetime.now(timezone.utc)
    if session.submitted_at is None:
        session.question_shown_at = now
        db.commit()
        db.refresh(session)

   
    q = session.question
    canonical = q.get_canonical_options()
    perm = str_to_permutation(session.shuffled_order)
    shuffled_options = [canonical[i] for i in perm]

    q_response = QuizQuestionResponse(
        session_id=session.id,
        quiz_run_id=quiz_run_id,
        question_index=session.question_index,
        total_questions=session.total_questions,
        prompt=sanitize_latex_to_unicode(q.prompt),
        options=[sanitize_latex_to_unicode(o) for o in shuffled_options],
        preview_coins=q.preview_coins,
        preview_xp=q.preview_xp,
        question_shown_at=session.question_shown_at,
        topic=q.topic,
        difficulty=q.difficulty,
    )

    return QuizNextResponse(finished=False, question=q_response)



@router.get(
    "/summary/{quiz_run_id}",
    response_model=QuizSummaryResponse,
    summary="Get post-quiz summary with transparent reward breakdown & notices",
)
def get_quiz_summary(
    quiz_run_id: str,
    current_user: models.User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
):
    """
    Returns aggregated post-quiz summary data.
    Transparently displays any safeguards triggered (e.g. cooldown violations, daily cap reductions).
    """
    sessions = (
        db.query(models.QuizSession)
        .filter_by(quiz_run_id=quiz_run_id)
        .order_by(models.QuizSession.question_index.asc())
        .all()
    )

    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz run not found.",
        )

    if sessions[0].user_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    total_q = len(sessions)
    answered = sum(1 for s in sessions if s.submitted_at is not None)
    correct = sum(1 for s in sessions if s.is_correct is True)
    accuracy_pct = round((correct / answered * 100), 1) if answered > 0 else 0.0

    total_coins = sum(s.coins_awarded for s in sessions)
    total_xp = sum(s.xp_awarded for s in sessions)

    rejections = sum(1 for s in sessions if s.rejection_reason is not None)

   
    flag_count = (
        db.query(models.RewardAuditLog)
        .filter(
            models.RewardAuditLog.user_id == current_user.id,
            models.RewardAuditLog.reason_code == models.ReasonCode.pattern_flagged,
            models.RewardAuditLog.created_at >= sessions[0].question_shown_at,
        )
        .count()
    )

    notices: List[str] = []
    cooldown_count = sum(1 for s in sessions if s.rejection_reason == "cooldown_violation")
    if cooldown_count > 0:
        notices.append(
            f"⚡ {cooldown_count} answer{'s were' if cooldown_count > 1 else ' was'} submitted faster than the {settings.QUESTION_MIN_COOLDOWN_SECONDS}s minimum threshold and could not qualify for rewards."
        )

    cap_count = sum(1 for s in sessions if s.rejection_reason == "cap_exceeded")
    if cap_count > 0:
        notices.append(
            f"🛡️ Daily earn limit reached ({settings.DAILY_MAX_COINS} coins / {settings.DAILY_MAX_XP} XP). Policy: {settings.CAP_EXCEEDED_POLICY}."
        )

    answers_summary: List[QuizAnswerSummary] = [
        QuizAnswerSummary(
            question_index=s.question_index,
            prompt=s.question.prompt,
            is_correct=s.is_correct,
            coins_awarded=s.coins_awarded,
            xp_awarded=s.xp_awarded,
            rejection_reason=s.rejection_reason,
        )
        for s in sessions
    ]

    return QuizSummaryResponse(
        quiz_run_id=quiz_run_id,
        total_questions=total_q,
        answered=answered,
        correct=correct,
        accuracy_pct=accuracy_pct,
        total_coins=total_coins,
        total_xp=total_xp,
        rejections=rejections,
        flags=flag_count,
        answers=answers_summary,
        transparency_notices=notices,
    )


# ─── PDF Export & Custom Teacher Quiz Builder ───────────────────────────────

import io
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Group


class TeacherQuestionIn(BaseModel):
    prompt: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option_index: int
    explanation: Optional[str] = None
    difficulty: str = "medium"


class TeacherQuizCreate(BaseModel):
    title: str
    topic: str
    description: Optional[str] = None
    time_limit_minutes: int = 15
    is_published: bool = True
    questions: List[TeacherQuestionIn]


class TeacherQuizSubmitRequest(BaseModel):
    answers: Dict[str, int]  # question_id (str) -> selected_option_index (int)


@router.get(
    "/{quiz_run_id}/download-pdf",
    summary="Download complete quiz question paper, answers and AI explanations as PDF",
)
def download_quiz_pdf(
    quiz_run_id: str,
    view: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Exports the student's quiz session into a formatted PDF document.
    Includes the student's selected answer, the correct answer, score summary,
    and step-by-step AI explanations.
    """
    sessions = (
        db.query(models.QuizSession)
        .filter_by(quiz_run_id=quiz_run_id)
        .order_by(models.QuizSession.question_index.asc())
        .all()
    )
    if not sessions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz run not found.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0B281D"),
    )
    sub_style = ParagraphStyle(
        "SubStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
    )
    q_title_style = ParagraphStyle(
        "QTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#103E2D"),
    )
    opt_style = ParagraphStyle(
        "OptStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1F2937"),
    )
    correct_opt_style = ParagraphStyle(
        "CorrectOptStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#059669"),
    )
    exp_style = ParagraphStyle(
        "ExpStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#374151"),
    )

    story = []

    # Header
    story.append(Paragraph("EklavyaX Academy — Quiz Question Paper & Review", title_style))
    topic = sessions[0].question.topic if sessions[0].question else "STEM Mastery"
    total_q = len(sessions)
    correct_q = sum(1 for s in sessions if s.is_correct)
    pct = round((correct_q / total_q * 100), 1) if total_q > 0 else 0

    story.append(
        Paragraph(
            f"<b>Student:</b> {current_user.username} &nbsp;|&nbsp; <b>Topic:</b> {topic} &nbsp;|&nbsp; "
            f"<b>Score:</b> {correct_q}/{total_q} ({pct}%) &nbsp;|&nbsp; <b>Date:</b> {datetime.now(timezone.utc).strftime('%d %b %Y')}",
            sub_style,
        )
    )
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#F4AE25"), spaceAfter=15))

    # Questions loop
    for i, s in enumerate(sessions, 1):
        q = s.question
        if not q:
            continue

        status_text = "<font color='#059669'><b>[CORRECT +10 Coins]</b></font>" if s.is_correct else "<font color='#DC2626'><b>[INCORRECT]</b></font>"
        story.append(Paragraph(f"<b>Question {i}:</b> {q.prompt} &nbsp; {status_text}", q_title_style))
        story.append(Spacer(1, 4))

        options = q.get_canonical_options()
        for opt_idx, opt_text in enumerate(options):
            label = chr(65 + opt_idx)  # A, B, C, D
            is_correct_opt = (opt_idx == q.correct_option_index)
            is_student_pick = (opt_idx == s.selected_option_index)

            marker = ""
            if is_correct_opt and is_student_pick:
                marker = " ✔ (Your Answer - Correct)"
                cur_style = correct_opt_style
            elif is_correct_opt:
                marker = " ✔ (Correct Answer)"
                cur_style = correct_opt_style
            elif is_student_pick:
                marker = " ✖ (Your Answer)"
                cur_style = ParagraphStyle("WrongOpt", parent=opt_style, textColor=colors.HexColor("#DC2626"))
            else:
                cur_style = opt_style

            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>({label})</b> {opt_text} {marker}", cur_style))
            story.append(Spacer(1, 2))

        # Explanation section
        story.append(Spacer(1, 4))
        explanation_text = q.explanation or "The correct concept follows standard scientific derivations and logical principles."
        story.append(Paragraph(f"<b>Detailed Explanation:</b> {explanation_text}", exp_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=10))

    # Footer note
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "<i>Generated by EklavyaX Synapse AI Learning Platform. All rights reserved.</i>",
            sub_style,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    filename = f"EklavyaX_Quiz_{quiz_run_id[:8]}.pdf"

    disp = "inline" if view else "attachment"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disp}; filename="{filename}"'},
    )



# ─── Custom Teacher Quiz Endpoints ──────────────────────────────────────────

@router.post("/custom/create", summary="Teacher creates custom quiz")
def create_custom_teacher_quiz(
    payload: TeacherQuizCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("teacher", "admin")),
):
    """Teacher creates a custom quiz with multiple questions."""
    t_quiz = models.TeacherQuiz(
        teacher_id=current_user.id,
        title=payload.title,
        topic=payload.topic,
        description=payload.description,
        time_limit_minutes=payload.time_limit_minutes,
        is_published=payload.is_published,
    )
    db.add(t_quiz)
    db.flush()

    for q_in in payload.questions:
        q_obj = models.TeacherQuizQuestion(
            quiz_id=t_quiz.id,
            prompt=q_in.prompt,
            option_a=q_in.option_a,
            option_b=q_in.option_b,
            option_c=q_in.option_c,
            option_d=q_in.option_d,
            correct_option_index=q_in.correct_option_index,
            explanation=q_in.explanation,
            difficulty=q_in.difficulty,
        )
        db.add(q_obj)

        # Also add to universal quiz_questions bank so students can practice them
        bank_q = models.QuizQuestion(
            topic=payload.topic,
            prompt=q_in.prompt,
            option_a=q_in.option_a,
            option_b=q_in.option_b,
            option_c=q_in.option_c,
            option_d=q_in.option_d,
            correct_option_index=q_in.correct_option_index,
            explanation=q_in.explanation,
            difficulty=q_in.difficulty,
        )
        db.add(bank_q)

    db.commit()

    return {
        "status": "created",
        "quiz_id": t_quiz.id,
        "title": t_quiz.title,
        "question_count": len(payload.questions),
    }


@router.get("/custom/list", summary="List custom quizzes created by teacher")
def list_custom_quizzes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List quizzes created by teacher or available to students."""
    query = db.query(models.TeacherQuiz)
    if current_user.role == models.UserRole.teacher:
        query = query.filter_by(teacher_id=current_user.id)
    else:
        query = query.filter_by(is_published=True)

    quizzes = query.order_by(models.TeacherQuiz.created_at.desc()).all()

    return {
        "quizzes": [
            {
                "id": q.id,
                "title": q.title,
                "topic": q.topic,
                "description": q.description,
                "time_limit_minutes": q.time_limit_minutes,
                "is_published": q.is_published,
                "question_count": len(q.questions),
                "created_at": q.created_at.isoformat(),
            }
            for q in quizzes
        ]
    }


@router.delete("/custom/{quiz_id}", summary="Delete custom quiz")
def delete_custom_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("teacher", "admin")),
):
    """Delete a custom quiz."""
    quiz = db.query(models.TeacherQuiz).filter_by(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    if quiz.teacher_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    db.delete(quiz)
    db.commit()

    return {"status": "deleted", "quiz_id": quiz_id}


# ─── Student Teacher Quiz Taking & Structured Analysis PDF ─────────────────

@router.get("/teacher/published-list", summary="List published quizzes available for students")
def get_published_teacher_quizzes(db: Session = Depends(get_db)) -> Dict[str, Any]:
    quizzes = (
        db.query(models.TeacherQuiz)
        .filter_by(is_published=True)
        .order_by(models.TeacherQuiz.created_at.desc())
        .all()
    )

    return {
        "quizzes": [
            {
                "id": q.id,
                "title": q.title,
                "topic": q.topic,
                "description": q.description or f"Comprehensive {q.topic} diagnostic test",
                "time_limit_minutes": q.time_limit_minutes,
                "question_count": len(q.questions),
                "teacher_name": q.teacher.username if q.teacher else "Faculty Mentor",
                "created_at": q.created_at.strftime("%d %b %Y"),
            }
            for q in quizzes
        ]
    }


@router.get("/teacher/{quiz_id}/start", summary="Student starts teacher quiz")
def start_teacher_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    quiz = db.query(models.TeacherQuiz).filter_by(id=quiz_id, is_published=True).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found or not published.")

    # Return questions with options without revealing correct_option_index
    questions_data = []
    for idx, q in enumerate(quiz.questions):
        questions_data.append({
            "id": q.id,
            "index": idx,
            "prompt": q.prompt,
            "options": [q.option_a, q.option_b, q.option_c, q.option_d],
            "difficulty": q.difficulty,
        })

    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "topic": quiz.topic,
        "time_limit_minutes": quiz.time_limit_minutes,
        "total_questions": len(questions_data),
        "teacher_name": quiz.teacher.username if quiz.teacher else "Faculty Mentor",
        "questions": questions_data,
    }


@router.post("/teacher/{quiz_id}/submit", summary="Student submits teacher quiz and gets scored against teacher answer key")
def submit_teacher_quiz(
    quiz_id: int,
    payload: TeacherQuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    quiz = db.query(models.TeacherQuiz).filter_by(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    evaluations = []
    correct_count = 0
    total_q = len(quiz.questions)

    for q in quiz.questions:
        student_ans = payload.answers.get(str(q.id))
        is_corr = (student_ans is not None and student_ans == q.correct_option_index)
        if is_corr:
            correct_count += 1

        options = [q.option_a, q.option_b, q.option_c, q.option_d]
        student_text = options[student_ans] if student_ans is not None and 0 <= student_ans < len(options) else "Not Attempted"
        correct_text = options[q.correct_option_index] if 0 <= q.correct_option_index < len(options) else "Option A"

        evaluations.append({
            "question_id": q.id,
            "prompt": q.prompt,
            "student_choice": student_text,
            "correct_choice": correct_text,
            "is_correct": is_corr,
            "explanation": q.explanation or "Standard step-by-step derivation according to faculty syllabus.",
        })

    accuracy = round((correct_count / max(total_q, 1)) * 100, 1)
    coins_earned = correct_count * 10
    xp_earned = correct_count * 20

    # Credit student's wallet
    if current_user.wallet:
        current_user.wallet.balance += coins_earned
        current_user.wallet.xp += xp_earned
    else:
        wallet = models.Wallet(user_id=current_user.id, balance=100 + coins_earned, xp=200 + xp_earned)
        db.add(wallet)

    submission = models.TeacherQuizSubmission(
        quiz_id=quiz.id,
        student_id=current_user.id,
        score=correct_count * 10,
        total_marks=total_q * 10,
        accuracy_percentage=accuracy,
        coins_awarded=coins_earned,
        xp_awarded=xp_earned,
        answers_json=json.dumps(evaluations),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "status": "evaluated",
        "submission_id": submission.id,
        "quiz_title": quiz.title,
        "score": correct_count * 10,
        "total_marks": total_q * 10,
        "correct_answers": correct_count,
        "total_questions": total_q,
        "accuracy_percentage": accuracy,
        "coins_awarded": coins_earned,
        "xp_awarded": xp_earned,
        "evaluations": evaluations,
    }


@router.get("/teacher/submission/{submission_id}/report-pdf", summary="Download or View structured diagnostic analysis report PDF with graphs")
def get_submission_analysis_pdf(
    submission_id: int,
    view: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Generates a structured, diagnostic ReportLab PDF report containing:
    - Institutional header & credentials
    - Performance metrics & EduCoins awarded
    - Graphical visual performance chart (Score & Accuracy Bar)
    - Comprehensive mistake analysis table with student choice, correct answer, and explanation.
    """
    sub = db.query(models.TeacherQuizSubmission).filter_by(id=submission_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    quiz = db.query(models.TeacherQuiz).filter_by(id=sub.quiz_id).first()
    evaluations = json.loads(sub.answers_json) if sub.answers_json else []

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("RTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#0B281D"))
    sub_title = ParagraphStyle("RSub", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#6366F1"))
    heading2 = ParagraphStyle("RH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#1E293B"))
    normal_style = ParagraphStyle("RNorm", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#334155"))
    bold_style = ParagraphStyle("RBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#0F172A"))
    correct_style = ParagraphStyle("RCorr", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#16A34A"))
    wrong_style = ParagraphStyle("RWrong", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#DC2626"))

    story = []

    # 1. Header Banner
    story.append(Paragraph("EklavyaX — Institutional Diagnostic Performance Report", title_style))
    story.append(Paragraph(f"Faculty Quiz: {quiz.title if quiz else 'Diagnostic Assessment'} • Topic: {quiz.topic if quiz else 'General STEM'}", sub_title))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0B281D"), spaceBefore=2, spaceAfter=10))

    # 2. Student & Assessment Info Card
    info_data = [
        [
            Paragraph(f"<b>Student Name:</b> {sub.student_id}", normal_style),
            Paragraph(f"<b>Date Taken:</b> {sub.submitted_at.strftime('%d %b %Y, %I:%M %p')}", normal_style),
        ],
        [
            Paragraph(f"<b>Total Score:</b> <b>{sub.score} / {sub.total_marks} pts</b>", normal_style),
            Paragraph(f"<b>Overall Accuracy:</b> <b>{sub.accuracy_percentage}%</b>", normal_style),
        ],
        [
            Paragraph(f"<b>EduCoins Awarded:</b> +{sub.coins_awarded} 🪙", bold_style),
            Paragraph(f"<b>Experience Gained:</b> +{sub.xp_awarded} XP ⚡", bold_style),
        ],
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))

    # 3. Graphical Performance Analysis Visual (Drawing)
    story.append(Paragraph("📊 Graphical Performance & Mastery Analysis", heading2))
    story.append(Spacer(1, 6))

    # Draw visual accuracy bar & gauge chart
    d = Drawing(540, 50)
    # Background bar
    d.add(Rect(0, 18, 540, 22, rx=6, ry=6, fillColor=colors.HexColor("#E2E8F0"), strokeColor=None))
    # Filled progress bar
    fill_width = max(10, int(540 * (sub.accuracy_percentage / 100.0)))
    bar_color = colors.HexColor("#10B981") if sub.accuracy_percentage >= 75 else (colors.HexColor("#F59E0B") if sub.accuracy_percentage >= 50 else colors.HexColor("#EF4444"))
    d.add(Rect(0, 18, fill_width, 22, rx=6, ry=6, fillColor=bar_color, strokeColor=None))
    # Labels
    d.add(String(10, 24, f"Student Accuracy: {sub.accuracy_percentage}%", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.white))
    d.add(String(0, 4, "0% (Foundation)", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))
    d.add(String(240, 4, "50% (Passing)", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))
    d.add(String(470, 4, "100% (Mastery)", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))
    story.append(d)
    story.append(Spacer(1, 16))

    # 4. Deep Question-by-Question Mistake Review Table
    story.append(Paragraph("📝 Question-by-Question Mistake Review & Step-by-Step Solutions", heading2))
    story.append(Spacer(1, 8))

    for idx, ev in enumerate(evaluations, 1):
        status_par = Paragraph("✅ CORRECT", correct_style) if ev.get("is_correct") else Paragraph("❌ MISTAKE / INCORRECT", wrong_style)
        card_data = [
            [
                Paragraph(f"<b>Question #{idx}:</b> {ev.get('prompt')}", bold_style),
                status_par,
            ],
            [
                Paragraph(f"<b>Your Choice:</b> {ev.get('student_choice')}", normal_style),
                Paragraph(f"<b>Teacher's Key:</b> <b>{ev.get('correct_choice')}</b>", normal_style),
            ],
            [
                Paragraph(f"<b>Explanation & Key Derivation:</b><br/>{ev.get('explanation')}", normal_style),
                "",
            ],
        ]
        q_table = Table(card_data, colWidths=[380, 160])
        border_col = colors.HexColor("#86EFAC") if ev.get("is_correct") else colors.HexColor("#FCA5A5")
        bg_col = colors.HexColor("#F0FDF4") if ev.get("is_correct") else colors.HexColor("#FEF2F2")
        q_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_col),
            ("BOX", (0, 0), (-1, -1), 1, border_col),
            ("SPAN", (0, 2), (1, 2)),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(q_table)
        story.append(Spacer(1, 8))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    filename = f"EklavyaX_Diagnostic_Report_Sub{submission_id}.pdf"
    disp = "inline" if view else "attachment"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disp}; filename="{filename}"'},
    )

