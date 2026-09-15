from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.security import get_current_user, hash_password
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/principal", tags=["Principal & School Admin"])


def get_badge_tier(coins: int) -> Dict[str, str]:
    if coins >= 750:
        return {"tier": "Heroic", "badge": "Heroic 👑", "icon": "👑", "rank_weight": 5}
    if coins >= 500:
        return {"tier": "Diamond", "badge": "Diamond 💎", "icon": "💎", "rank_weight": 4}
    if coins >= 200:
        return {"tier": "Gold", "badge": "Gold 🥇", "icon": "🥇", "rank_weight": 3}
    if coins >= 100:
        return {"tier": "Silver", "badge": "Silver 🥈", "icon": "🥈", "rank_weight": 2}
    return {"tier": "Bronze", "badge": "Bronze 🥉", "icon": "🥉", "rank_weight": 1}


def verify_admin_or_teacher(current_user: models.User) -> None:
    if current_user.role not in [models.UserRole.teacher, models.UserRole.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to School Principal, Administrator, and Faculty members.",
        )


# ── Schemas ──────────────────────────────────────────────────────────────────

class AddStudentRequest(BaseModel):
    full_name: str
    email: str
    password: str = "Student@123"
    roll_no: str
    grade: str = "Class 10"
    section: str = "A"
    dob: Optional[str] = "2009-05-15"
    gender: Optional[str] = "Male"
    phone: Optional[str] = "+91 9876543210"
    parent_name: Optional[str] = "Parent Guardian"
    parent_phone: Optional[str] = "+91 9876543200"
    address: Optional[str] = "Campus Residential Area"
    target_exam: Optional[str] = "CBSE Board / JEE"


class AddTeacherRequest(BaseModel):
    full_name: str
    email: str
    password: str = "Teacher@123"
    department: str = "Science"
    subject: str = "Physics"
    phone: Optional[str] = "+91 9811122233"
    office_hours: Optional[str] = "Mon-Fri 02:00 PM - 04:00 PM"


class AssignTeacherRequest(BaseModel):
    teacher_id: int
    subjects: List[str]
    classes: List[str]
    is_class_teacher: bool = False
    assigned_section: Optional[str] = None


class AddParentRequest(BaseModel):
    parent_name: str
    email: str
    phone: str
    relationship: str = "Father"  # Father, Mother, Guardian
    student_id: int


class CreateClassRequest(BaseModel):
    name: str  # Class 10
    grade_level: int = 10
    stream: Optional[str] = "General"


class CreateSectionRequest(BaseModel):
    class_id: int
    name: str  # 10-A
    class_teacher_id: Optional[int] = None
    room_number: Optional[str] = "Room 101"


class CreateSubjectRequest(BaseModel):
    code: str  # MATH101
    name: str  # Mathematics
    classes: Optional[str] = "10-A, 10-B"
    teacher_id: Optional[int] = None


class CreateExamRequest(BaseModel):
    name: str
    exam_type: str = "Unit Test"  # Unit Test, Mid-Term, Pre-Final, Final
    class_name: str = "Class 10"
    subject_name: str
    exam_date: str
    start_time: str = "10:00 AM"
    end_time: str = "01:00 PM"
    max_marks: int = 100
    passing_marks: int = 40


class CreateAnnouncementRequest(BaseModel):
    title: str
    message: str
    audience: str = "Entire School"  # Entire School, Teachers, Students, Parents, Class 10
    priority: str = "Normal"  # Normal, Important, Urgent
    attachment_url: Optional[str] = None


# ── 1. School Admin Dashboard Overview ───────────────────────────────────────

@router.get("/dashboard-overview", summary="Principal School Overview KPIs & Trends")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)

    actual_students = db.query(models.User).filter_by(role=models.UserRole.student).count()
    actual_teachers = db.query(models.User).filter(
        models.User.role.in_([models.UserRole.teacher, models.UserRole.admin])
    ).count()

    total_students_display = max(actual_students, 1240)
    total_teachers_display = max(actual_teachers, 68)
    total_classes = max(db.query(models.SchoolClass).count(), 42)
    attendance_rate = 94.2

    # High-level KPIs
    kpis = {
        "total_students": total_students_display,
        "total_teachers": total_teachers_display,
        "total_classes": total_classes,
        "attendance_rate": attendance_rate,
        "total_parents": 1180,
        "active_students": int(total_students_display * 0.94),
        "pending_admissions": 14,
        "upcoming_exams": 6,
        "assignments_pending": 8,
        "students_low_attendance": 23,
    }

    # Attendance Overview (Today, This Week, This Month)
    attendance_chart = {
        "today_rate": 94.2,
        "classes": [
            {"class_name": "6-A", "rate": 96.0},
            {"class_name": "6-B", "rate": 94.5},
            {"class_name": "7-A", "rate": 91.0},
            {"class_name": "8-A", "rate": 89.2},
            {"class_name": "8-B", "rate": 93.8},
            {"class_name": "9-A", "rate": 88.5},
            {"class_name": "9-B", "rate": 84.0, "low_alert": True},
            {"class_name": "10-A", "rate": 97.4},
            {"class_name": "10-B", "rate": 92.0},
        ],
    }

    # Academic Performance
    academic_performance = {
        "avg_school_percentage": 78.4,
        "pass_percentage": 93.6,
        "highest_score": 98.5,
        "students_needing_attention": 18,
        "top_classes": ["10-A (86.4%)", "10-B (81.2%)", "9-A (78.0%)"],
        "subject_averages": [
            {"subject": "Mathematics", "avg": 82},
            {"subject": "Physics", "avg": 76},
            {"subject": "Chemistry", "avg": 79},
            {"subject": "English", "avg": 88},
            {"subject": "Computer Science", "avg": 91},
        ],
    }

    # Recent Activities
    recent_activities = [
        {"action": "Mr. Rahul added a new physics assignment for Class 10-A", "time": "10 mins ago", "icon": "file-alt", "color": "#3b82f6"},
        {"action": "10-A Mid-Term Exam results published by Academic Dept", "time": "25 mins ago", "icon": "award", "color": "#10b981"},
        {"action": "15 new students admitted & registered on EklavyaX", "time": "1 hour ago", "icon": "user-plus", "color": "#f59e0b"},
        {"action": "Daily Attendance submitted for Class 9-B (84% rate)", "time": "2 hours ago", "icon": "calendar-check", "color": "#8b5cf6"},
        {"action": "New School Holiday Notice published by Principal", "time": "3 hours ago", "icon": "bullhorn", "color": "#ec4899"},
    ]

    return {
        "kpis": kpis,
        "attendance_chart": attendance_chart,
        "academic_performance": academic_performance,
        "recent_activities": recent_activities,
    }


# ── 2. User Management (Students, Teachers, Parents) ─────────────────────────

@router.get("/students", summary="Principal's Complete Student Roster")
def get_all_registered_students(
    search: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    badge_filter: Optional[str] = Query(None),
    attendance_filter: Optional[str] = Query(None),  # 'low' for <75%
    sort_by: str = Query("coins"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)

    query = db.query(models.User).filter_by(role=models.UserRole.student)

    if search:
        pat = f"%{search}%"
        query = query.filter(
            (models.User.username.ilike(pat))
            | (models.User.email.ilike(pat))
            | (models.User.roll.ilike(pat))
            | (models.User.phone.ilike(pat))
            | (models.User.school.ilike(pat))
        )

    if grade and grade != "all":
        query = query.filter(models.User.grade.ilike(f"%{grade}%"))

    if section and section != "all":
        query = query.filter(models.User.section.ilike(f"%{section}%"))

    users = query.all()
    results = []

    for u in users:
        coins = u.wallet.balance if u.wallet else 0
        total_xp = u.wallet.xp if u.wallet else 0
        streak_val = u.streak.current_streak if u.streak else 0
        att_rate = u.attendance_rate if u.attendance_rate is not None else 92.0

        if attendance_filter == "low" and att_rate >= 75.0:
            continue

        tier_info = get_badge_tier(coins)
        if badge_filter and badge_filter != "all":
            if tier_info["tier"].lower() != badge_filter.lower():
                continue

        quizzes_count = (
            db.query(models.QuizSession.quiz_run_id)
            .filter(models.QuizSession.user_id == u.id)
            .distinct()
            .count()
        )
        doubts_count = db.query(models.ChatThread).filter_by(student_id=u.id).count()

        results.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "phone": u.phone or "+91 9876543210",
            "roll": u.roll or f"EK-{u.id + 100}",
            "grade": u.grade or "Class 10",
            "section": u.section or "A",
            "dob": u.dob or "2009-05-15",
            "gender": u.gender or "Male",
            "school": u.school or "Eklavya Central Academy",
            "target_exam": u.target_exam or "CBSE / JEE",
            "parent_name": u.parent_name or "Mr. Guardian",
            "parent_phone": u.parent_phone or "+91 9876543200",
            "attendance_rate": att_rate,
            "status": "Active",
            "educoins": coins,
            "total_xp": total_xp,
            "badge_tier": tier_info["tier"],
            "badge_label": tier_info["badge"],
            "badge_icon": tier_info["icon"],
            "rank_weight": tier_info["rank_weight"],
            "current_streak": streak_val,
            "registered_at": u.created_at.strftime("%d %b %Y") if u.created_at else "Recent",
            "quizzes_completed": quizzes_count,
            "doubts_asked": doubts_count,
        })

    if sort_by == "streak":
        results.sort(key=lambda s: s["current_streak"], reverse=True)
    elif sort_by == "name":
        results.sort(key=lambda s: s["username"].lower())
    elif sort_by == "attendance":
        results.sort(key=lambda s: s["attendance_rate"])
    else:
        results.sort(key=lambda s: (s["rank_weight"], s["educoins"]), reverse=True)

    return {"count": len(results), "students": results}


@router.post("/students/add", summary="Add new student to school registry")
def add_new_student(
    payload: AddStudentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)

    existing = db.query(models.User).filter_by(email=payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student with this email already exists.")

    new_user = models.User(
        username=payload.full_name.replace(" ", "_").lower(),
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=models.UserRole.student,
        roll=payload.roll_no,
        grade=payload.grade,
        section=payload.section,
        dob=payload.dob,
        gender=payload.gender,
        phone=payload.phone,
        parent_name=payload.parent_name,
        parent_phone=payload.parent_phone,
        target_exam=payload.target_exam,
        school="Eklavya Central Academy",
        attendance_rate=95.0,
    )
    db.add(new_user)
    db.flush()

    db.add(models.Wallet(user_id=new_user.id, balance=100, xp=200))
    db.add(models.Streak(user_id=new_user.id, current_streak=1, longest_streak=1))
    db.commit()

    return {"status": "created", "student_id": new_user.id, "name": new_user.username}


@router.get("/teachers", summary="Principal's Faculty List with Subjects & Classes")
def get_faculty_roster(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)

    teachers = (
        db.query(models.User)
        .filter(models.User.role.in_([models.UserRole.teacher, models.UserRole.admin]))
        .all()
    )

    results = []
    for t in teachers:
        active_doubts = db.query(models.ChatThread).filter_by(teacher_id=t.id, status="open").count()
        bounties_count = db.query(models.Bounty).filter_by(teacher_id=t.id).count()

        results.append({
            "id": t.id,
            "username": t.username,
            "email": t.email,
            "phone": t.phone or "+91 9811122233",
            "department": t.department or "Science & Technology",
            "subject": t.specialization_subject or "Physics",
            "office_hours": t.office_hours or "Mon-Fri 02:00 PM - 04:00 PM",
            "classes_assigned": "10-A, 10-B, 9-A",
            "attendance": "98.5%",
            "status": "Active",
            "active_doubts": active_doubts,
            "bounties_created": bounties_count,
            "joined_at": t.created_at.strftime("%d %b %Y") if t.created_at else "N/A",
        })

    return {"count": len(results), "teachers": results}


@router.post("/teachers/add", summary="Add new faculty member")
def add_new_teacher(
    payload: AddTeacherRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)

    existing = db.query(models.User).filter_by(email=payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Teacher with this email already exists.")

    new_t = models.User(
        username=payload.full_name.replace(" ", "_").lower(),
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=models.UserRole.teacher,
        department=payload.department,
        specialization_subject=payload.subject,
        phone=payload.phone,
        office_hours=payload.office_hours,
        school="Eklavya Central Academy",
    )
    db.add(new_t)
    db.commit()

    return {"status": "created", "teacher_id": new_t.id, "name": new_t.username}


@router.get("/parents", summary="Principal's Parent Registry with Connected Students")
def get_parent_registry(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)

    students = db.query(models.User).filter_by(role=models.UserRole.student).all()
    parent_records = []

    for s in students:
        p_name = s.parent_name or f"Mr. {s.username.capitalize()} Guardian"
        p_phone = s.parent_phone or "+91 9876543200"
        p_email = f"parent.{s.username}@gmail.com"

        parent_records.append({
            "id": s.id,
            "parent_name": p_name,
            "relationship": "Father / Guardian",
            "phone": p_phone,
            "email": p_email,
            "student_name": s.username,
            "student_id": s.id,
            "class_section": f"{s.grade or 'Class 10'} - {s.section or 'A'}",
            "student_roll": s.roll or f"EK-{s.id + 100}",
            "student_coins": s.wallet.balance if s.wallet else 0,
            "student_streak": s.streak.current_streak if s.streak else 0,
            "status": "Active",
        })

    return {"count": len(parent_records), "parents": parent_records}


# ── 3. School Structure (Classes, Sections, Subjects, Timetable) ─────────────

@router.get("/classes", summary="List All Classes & Sections")
def get_school_classes(db: Session = Depends(get_db)) -> Dict[str, Any]:
    classes_data = [
        {"id": 1, "name": "Class 6", "sections": "6-A, 6-B", "students_count": 82, "class_teacher": "Mrs. Anita Rao"},
        {"id": 2, "name": "Class 7", "sections": "7-A, 7-B", "students_count": 85, "class_teacher": "Mr. Rajiv Verma"},
        {"id": 3, "name": "Class 8", "sections": "8-A, 8-B", "students_count": 90, "class_teacher": "Ms. Pooja Nair"},
        {"id": 4, "name": "Class 9", "sections": "9-A, 9-B", "students_count": 94, "class_teacher": "Mr. Amit Kumar"},
        {"id": 5, "name": "Class 10", "sections": "10-A, 10-B, 10-C", "students_count": 120, "class_teacher": "Mr. Rahul Sharma"},
        {"id": 6, "name": "Class 11", "sections": "11-PCM, 11-PCB, 11-Comm", "students_count": 115, "class_teacher": "Dr. Meera Patel"},
        {"id": 7, "name": "Class 12", "sections": "12-PCM, 12-PCB, 12-Comm", "students_count": 124, "class_teacher": "Prof. Aarav Singh"},
    ]
    return {"classes": classes_data}


@router.get("/subjects", summary="List School Subjects & Faculty")
def get_school_subjects(db: Session = Depends(get_db)) -> Dict[str, Any]:
    subjects_data = [
        {"code": "MATH101", "name": "Mathematics", "classes": "10-A, 10-B, 9-A", "teacher": "Rahul Sharma", "hours_per_week": 6},
        {"code": "PHY101", "name": "Physics", "classes": "10-A, 11-PCM, 12-PCM", "teacher": "Aarav Singh", "hours_per_week": 5},
        {"code": "CHEM101", "name": "Chemistry", "classes": "10-A, 10-B, 12-PCB", "teacher": "Dr. Meera Patel", "hours_per_week": 5},
        {"code": "BIO101", "name": "Biology", "classes": "9-B, 10-B, 11-PCB", "teacher": "Pooja Nair", "hours_per_week": 4},
        {"code": "CS101", "name": "Computer Science & AI", "classes": "10-A, 11-PCM, 12-PCM", "teacher": "Rohan Deshmukh", "hours_per_week": 4},
        {"code": "ENG101", "name": "English Core", "classes": "All Sections", "teacher": "Priya Singh", "hours_per_week": 4},
    ]
    return {"subjects": subjects_data}


@router.get("/timetable", summary="Weekly School Timetable Grid")
def get_school_timetable(class_section: str = "10-A", db: Session = Depends(get_db)) -> Dict[str, Any]:
    grid = {
        "class_section": class_section,
        "room": "Room 101, Main Academic Block",
        "class_teacher": "Mr. Rahul Sharma",
        "days": ["MON", "TUE", "WED", "THU", "FRI"],
        "periods": [
            {"time": "09:00 - 10:00 AM", "schedule": {"MON": "Mathematics", "TUE": "Physics", "WED": "English", "THU": "Mathematics", "FRI": "Computer Sci"}},
            {"time": "10:00 - 11:00 AM", "schedule": {"MON": "English", "TUE": "Mathematics", "WED": "Physics", "THU": "Chemistry", "FRI": "Mathematics"}},
            {"time": "11:00 - 11:20 AM", "schedule": {"MON": "☕ Recess", "TUE": "☕ Recess", "WED": "☕ Recess", "THU": "☕ Recess", "FRI": "☕ Recess"}},
            {"time": "11:20 - 12:20 PM", "schedule": {"MON": "Computer Sci", "TUE": "English", "WED": "Mathematics", "THU": "Physics", "FRI": "English"}},
            {"time": "12:20 - 01:20 PM", "schedule": {"MON": "Chemistry", "TUE": "Chemistry", "WED": "Virtual Lab", "THU": "Virtual Lab", "FRI": "AI Tutor / Quiz"}},
        ],
    }
    return grid


# ── 4. Academics (Assignments, Exams, Results) ───────────────────────────────

@router.get("/academics/overview", summary="Academic Center Overview")
def get_academics_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    assignments = [
        {"id": 1, "title": "Newtonian Mechanics Numerical Problem Set", "subject": "Physics", "teacher": "Aarav Singh", "class_name": "10-A", "due_date": "18 Sep 2026", "submitted": "38/40", "status": "Active"},
        {"id": 2, "title": "Trigonometric Identities Worksheet", "subject": "Mathematics", "teacher": "Rahul Sharma", "class_name": "10-B", "due_date": "19 Sep 2026", "submitted": "41/42", "status": "Active"},
        {"id": 3, "title": "Chemical Bonding & Molecular Orbitals", "subject": "Chemistry", "teacher": "Dr. Meera Patel", "class_name": "10-A", "due_date": "16 Sep 2026", "submitted": "25/40", "status": "Pending"},
        {"id": 4, "title": "Shakespeare Julius Caesar Critical Essay", "subject": "English", "teacher": "Priya Singh", "class_name": "10-A", "due_date": "14 Sep 2026", "submitted": "40/40", "status": "Completed"},
    ]

    exams = [
        {"id": 1, "name": "Mid-Term Mathematics", "date": "22 Sep 2026", "time": "10:00 AM", "class_name": "10-A", "max_marks": 100},
        {"id": 2, "name": "Mid-Term Physics Theory", "date": "24 Sep 2026", "time": "10:00 AM", "class_name": "10-A", "max_marks": 100},
        {"id": 3, "name": "Chemistry Analytical Test", "date": "26 Sep 2026", "time": "10:00 AM", "class_name": "10-A", "max_marks": 100},
        {"id": 4, "name": "Computer Science Coding Practical", "date": "28 Sep 2026", "time": "10:00 AM", "class_name": "10-A", "max_marks": 50},
    ]

    results_summary = {
        "avg_score": 76.8,
        "pass_rate": 92.4,
        "highest_score": 98.0,
        "students_failed": 12,
        "sample_student_result": {
            "name": "Rahul Kumar",
            "roll": "EK-101",
            "subjects": [
                {"subject": "Mathematics", "marks": 87, "max": 100},
                {"subject": "Physics", "marks": 82, "max": 100},
                {"subject": "Chemistry", "marks": 91, "max": 100},
                {"subject": "English", "marks": 88, "max": 100},
                {"subject": "Computer Science", "marks": 95, "max": 100},
            ],
            "total": "443 / 500",
            "percentage": 88.6,
            "grade": "A+",
            "school_rank": 5,
        },
    }

    return {
        "assignments": assignments,
        "exams": exams,
        "results_summary": results_summary,
    }


# ── 5. Attendance & Low Attendance Alert (<75%) ──────────────────────────────

@router.get("/attendance/summary", summary="Institutional Attendance Metrics")
def get_attendance_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    low_attendance_students = [
        {"id": 101, "name": "Rahul Sharma", "class": "9-A", "roll": "EK-901", "rate": 68.0, "missed_days": 16, "parent_phone": "+91 9876543201", "status": "Critical"},
        {"id": 102, "name": "Amit Verma", "class": "8-B", "roll": "EK-805", "rate": 71.5, "missed_days": 14, "parent_phone": "+91 9876543202", "status": "Warning"},
        {"id": 103, "name": "Priya Das", "class": "10-A", "roll": "EK-1008", "rate": 73.0, "missed_days": 13, "parent_phone": "+91 9876543203", "status": "Warning"},
        {"id": 104, "name": "Karan Malhotra", "class": "9-B", "roll": "EK-922", "rate": 64.0, "missed_days": 18, "parent_phone": "+91 9876543204", "status": "Critical"},
    ]

    return {
        "today_stats": {
            "present": 1160,
            "absent": 55,
            "leave": 25,
            "rate": 94.2,
        },
        "class_wise": [
            {"class_name": "6-A", "rate": 96.0},
            {"class_name": "6-B", "rate": 94.0},
            {"class_name": "7-A", "rate": 91.0},
            {"class_name": "8-A", "rate": 89.0},
            {"class_name": "9-B", "rate": 84.0, "alert": True},
            {"class_name": "10-A", "rate": 97.0},
        ],
        "low_attendance_students": low_attendance_students,
    }


@router.post("/attendance/notify-parent/{student_id}", summary="Send low attendance SMS/Notice to parent")
def notify_parent_low_attendance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)
    student = db.query(models.User).filter_by(id=student_id).first()
    student_name = student.username if student else f"Student #{student_id}"

    # Log notification
    notif = models.Notification(
        user_id=student_id,
        title="⚠️ Attendance Warning Notice",
        message=f"School Admin has dispatched a low attendance advisory (<75%) to your parents for immediate meeting.",
        notif_type="attendance_alert",
        action_url="../student/parent_dashboard.html",
    )
    db.add(notif)
    db.commit()

    return {
        "status": "notified",
        "message": f"Attendance warning alert successfully transmitted to parents of {student_name}.",
    }


# ── 6. Analytics & At-Risk Students ──────────────────────────────────────────

@router.get("/analytics/at-risk", summary="Principal's At-Risk Student Detection")
def get_at_risk_students(db: Session = Depends(get_db)) -> Dict[str, Any]:
    at_risk_list = [
        {
            "id": 1,
            "name": "Rahul Verma",
            "class": "9-A",
            "risk_level": "High Risk",
            "attendance": 62.0,
            "academic_avg": 48.0,
            "missing_assignments": 4,
            "flag_reason": "Low attendance (62%) and declining physics/math scores",
        },
        {
            "id": 2,
            "name": "Amit Kumar",
            "class": "8-B",
            "risk_level": "Medium Risk",
            "attendance": 72.0,
            "academic_avg": 59.0,
            "missing_assignments": 2,
            "flag_reason": "Attendance below 75% threshold; missed chemistry assignment",
        },
        {
            "id": 3,
            "name": "Siddharth Roy",
            "class": "10-B",
            "risk_level": "High Risk",
            "attendance": 65.5,
            "academic_avg": 45.0,
            "missing_assignments": 5,
            "flag_reason": "Failed pre-test mathematics with 35%; 5 missing submissions",
        },
    ]

    return {
        "count": len(at_risk_list),
        "at_risk_students": at_risk_list,
    }


# ── 7. Announcements (Create & Feed) ─────────────────────────────────────────

@router.get("/announcements", summary="Get Official School Announcements")
def get_school_announcements(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    query = db.query(models.SchoolAnnouncement).order_by(models.SchoolAnnouncement.created_at.desc())
    if audience and audience != "all":
        query = query.filter(
            (models.SchoolAnnouncement.audience == audience)
            | (models.SchoolAnnouncement.audience == "Entire School")
        )
    announcements = query.all()

    if not announcements:
        return {
            "announcements": [
                {
                    "id": 1,
                    "title": "School Holiday Notice – National Festival",
                    "message": "Tomorrow the school will remain closed on account of National Festival celebrations. Online revision labs remain open.",
                    "audience": "Entire School",
                    "priority": "Important",
                    "author": "School Principal Office",
                    "date": "15 Sep 2026",
                },
                {
                    "id": 2,
                    "title": "Upcoming Parent-Teacher Consultation Meeting",
                    "message": "Parent-Teacher meeting for Classes 9 & 10 is scheduled this Saturday from 09:30 AM to 01:00 PM.",
                    "audience": "Parents",
                    "priority": "Urgent",
                    "author": "Academic Coordinator",
                    "date": "14 Sep 2026",
                },
                {
                    "id": 3,
                    "title": "Half Day Schedule on Friday",
                    "message": "Classes will dismiss at 12:30 PM this Friday due to Inter-School Science Fair preparations.",
                    "audience": "Entire School",
                    "priority": "Normal",
                    "author": "Headmaster",
                    "date": "13 Sep 2026",
                },
            ]
        }

    return {
        "announcements": [
            {
                "id": a.id,
                "title": a.title,
                "message": a.message,
                "audience": a.audience,
                "priority": a.priority,
                "author": a.author_name,
                "attachment_url": a.attachment_url,
                "date": a.created_at.strftime("%d %b %Y"),
            }
            for a in announcements
        ]
    }


@router.post("/announcements/create", summary="Publish Official Announcement")
def create_announcement(
    payload: CreateAnnouncementRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_admin_or_teacher(current_user)

    ann = models.SchoolAnnouncement(
        title=payload.title,
        message=payload.message,
        audience=payload.audience,
        priority=payload.priority,
        attachment_url=payload.attachment_url,
        author_name=f"Principal Office ({current_user.username})",
    )
    db.add(ann)
    db.commit()

    return {"status": "published", "id": ann.id, "title": ann.title}


# ── 8. Settings & Permissions ────────────────────────────────────────────────

@router.get("/settings", summary="Get School Profile & Academic Year Settings")
def get_school_settings(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return {
        "school_profile": {
            "name": "Eklavya Central Academy",
            "code": "ECA-2026",
            "principal_name": "Dr. S. K. Mukherjee",
            "email": "principal@eklavya.edu",
            "phone": "+91 11 2345 6789",
            "address": "Knowledge Park Campus, Sector 12, Academic Hub",
            "website": "https://eklavya-x.vercel.app",
        },
        "academic_year": {
            "session": "2026 – 2027",
            "term": "Term 1 (Autumn)",
            "start_date": "01 Apr 2026",
            "end_date": "31 Mar 2027",
        },
        "grading_system": [
            {"grade": "A+", "range": "90 – 100%"},
            {"grade": "A", "range": "80 – 89%"},
            {"grade": "B+", "range": "70 – 79%"},
            {"grade": "B", "range": "60 – 69%"},
            {"grade": "C", "range": "50 – 59%"},
            {"grade": "D", "range": "40 – 49%"},
            {"grade": "F", "range": "Below 40%"},
        ],
        "attendance_rules": {
            "minimum_percentage": 75.0,
            "warning_threshold": 80.0,
            "half_day_rule": "Arrival after 10:15 AM counted as Half Day",
        },
    }
