from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/study-planner", tags=["Study Planner & Exam Countdown"])

EXAM_DEFAULT_TOPICS = {
    "JEE Main": [
        "Kinematics & Projectile Motion",
        "Newton's Laws of Motion & Friction",
        "Thermodynamics & Heat Transfer",
        "Chemical Bonding & Molecular Structure",
        "Organic Reactions & Mechanisms",
        "Definite Integrals & Areas",
        "Coordinate Geometry & Conic Sections",
        "Electromagnetism & Faraday's Laws",
    ],
    "NEET": [
        "Cell Biology & Cell Cycle",
        "Human Physiology: Digestion & Respiration",
        "Genetics & Evolution",
        "Chemical Equilibrium & Ionic Equilibrium",
        "Plant Physiology & Photosynthesis",
        "Optics & Wave Motion",
        "Biomolecules & Polymers",
    ],
    "CBSE Class 12": [
        "Electrostatics & Capacitance",
        "Differential Equations & Matrices",
        "Aldehydes, Ketones & Carboxylic Acids",
        "Modern Physics & Semiconductor Devices",
        "Probability & Linear Programming",
    ],
    "General": [
        "Fundamental Concepts Revision",
        "Daily Practice Problems (DPP) Set 1",
        "Formula Sheet & Key Derivations",
        "Speed Quiz & Error Analysis",
        "Full Length Mock Test Section",
    ],
}


class SetupPlanRequest(BaseModel):
    target_exam: str
    target_date: str  # YYYY-MM-DD


@router.get("/plan", summary="Get user's current study plan and countdown")
def get_study_plan(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve exam countdown and daily study schedule."""
    tasks = (
        db.query(models.StudyPlanTask)
        .filter_by(user_id=current_user.id)
        .order_by(models.StudyPlanTask.day_number.asc())
        .all()
    )

    if not tasks:
        # Default plan suggestion
        target_exam = current_user.target_exam or "JEE Main"
        today = datetime.now(timezone.utc).date()
        target_date = today + timedelta(days=90)
        return {
            "has_plan": False,
            "suggested_exam": target_exam,
            "days_left": 90,
            "target_date": target_date.isoformat(),
            "tasks": [],
            "completion_rate": 0.0,
        }

    first_task = tasks[0]
    today = datetime.now(timezone.utc).date()
    days_left = max(0, (first_task.target_date - today).days)

    completed_count = sum(1 for t in tasks if t.is_completed)
    total_count = len(tasks)
    completion_rate = round((completed_count / total_count * 100), 1) if total_count > 0 else 0.0

    task_list = []
    for t in tasks:
        subtasks = []
        try:
            subtasks = json.loads(t.subtasks)
        except Exception:
            subtasks = []

        task_list.append({
            "id": t.id,
            "day_number": t.day_number,
            "topic": t.topic,
            "subtasks": subtasks,
            "is_completed": t.is_completed,
            "xp_reward": t.xp_reward,
        })

    return {
        "has_plan": True,
        "target_exam": first_task.target_exam,
        "target_date": first_task.target_date.isoformat(),
        "days_left": days_left,
        "completed_count": completed_count,
        "total_tasks": total_count,
        "completion_rate": completion_rate,
        "tasks": task_list,
    }


@router.post("/setup", summary="Set target exam and generate daily study schedule")
def setup_study_plan(
    payload: SetupPlanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Configures exam date and creates structured daily milestones."""
    try:
        target_dt = datetime.strptime(payload.target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target date format galat hai. Use YYYY-MM-DD.",
        )

    # Clean old plan
    db.query(models.StudyPlanTask).filter_by(user_id=current_user.id).delete()

    # Update user's profile target_exam
    current_user.target_exam = payload.target_exam

    topic_pool = EXAM_DEFAULT_TOPICS.get(payload.target_exam, EXAM_DEFAULT_TOPICS["General"])

    # Create 14 structured daily tasks
    created_tasks = []
    for day in range(1, 15):
        topic = topic_pool[(day - 1) % len(topic_pool)]
        subtasks = [
            f"Theory & Formula revision ({topic})",
            f"Solve 10 practice questions on {topic}",
            "Analyze incorrect answers in Flashcards",
        ]
        t = models.StudyPlanTask(
            user_id=current_user.id,
            target_exam=payload.target_exam,
            target_date=target_dt,
            day_number=day,
            topic=topic,
            subtasks=json.dumps(subtasks),
            is_completed=False,
            xp_reward=25,
        )
        db.add(t)
        created_tasks.append(t)

    db.commit()

    return {
        "status": "created",
        "target_exam": payload.target_exam,
        "tasks_generated": len(created_tasks),
    }


@router.post("/tasks/{task_id}/toggle", summary="Toggle completion status of a study task")
def toggle_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Toggle a task as done/undone and award daily XP."""
    task = db.query(models.StudyPlanTask).filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.is_completed = not task.is_completed
    task.completed_at = datetime.now(timezone.utc) if task.is_completed else None

    if task.is_completed and current_user.wallet:
        current_user.wallet.xp += task.xp_reward

    db.commit()

    return {
        "status": "toggled",
        "task_id": task.id,
        "is_completed": task.is_completed,
        "xp_awarded": task.xp_reward if task.is_completed else 0,
    }
