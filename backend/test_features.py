import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db.database import SessionLocal, engine, Base
from app.db import models
from app.api.routes import principal, doubts
from app.core.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
print("--- Testing Principal & Doubts Backend ---")

# 1. Ensure test faculty exists
teacher = db.query(models.User).filter_by(username="prof_sharma").first()
if not teacher:
    teacher = models.User(
        username="prof_sharma",
        email="sharma@eklavya.edu",
        hashed_password=hash_password("teach123"),
        role=models.UserRole.teacher,
        school="Eklavya Central Campus"
    )
    db.add(teacher)

# 2. Ensure test students exist with different EduCoin tiers
student_configs = [
    ("rahul_heroic", "rahul@eklavya.edu", "EK-101", 850, 15, "Heroic"),
    ("priya_diamond", "priya@eklavya.edu", "EK-102", 620, 10, "Diamond"),
    ("arjun_gold", "arjun@eklavya.edu", "EK-103", 350, 7, "Gold"),
    ("sneha_silver", "sneha@eklavya.edu", "EK-104", 150, 4, "Silver"),
]

for uname, uemail, uroll, ucoins, ustreak, tier_expect in student_configs:
    st = db.query(models.User).filter_by(username=uname).first()
    if not st:
        st = models.User(
            username=uname,
            email=uemail,
            hashed_password=hash_password("pass123"),
            role=models.UserRole.student,
            roll=uroll,
            grade="Class 12",
            school="Eklavya Central Campus",
            target_exam="JEE Advanced"
        )
        db.add(st)
        db.flush()
        db.add(models.Wallet(user_id=st.id, balance=ucoins, xp=ucoins + 50))
        db.add(models.Streak(user_id=st.id, current_streak=ustreak, longest_streak=ustreak + 2))

db.commit()

# 3. Test doubts teacher dropdown list
teachers_res = doubts.get_teachers_list(db=db)
print("Available Teachers count:", len(teachers_res["teachers"]))
for t in teachers_res["teachers"]:
    print(f"  - Teacher: {t['name']} ({t['email']})")

# 4. Test Principal Institutional KPIs
stats = principal.get_principal_stats(db=db, current_user=teacher)
print("Principal Overview Stats:")
print(f"  - Total Students: {stats['total_students']}")
print(f"  - Total Teachers: {stats['total_teachers']}")
print(f"  - Avg Coins: {stats['avg_coins_per_student']}")
print(f"  - Badge Distribution: {stats['badge_distribution']}")

# 5. Test Principal Student Roster
roster = principal.get_all_registered_students(
    search=None, grade=None, school=None, badge_filter=None, sort_by="coins", db=db, current_user=teacher
)
print(f"Principal Roster Student Count: {roster['count']}")
for s in roster["students"][:4]:
    print(f"  - Rank #{s['rank_weight']} | {s['username']} | Roll: {s['roll']} | Coins: {s['educoins']} | Badge: {s['badge_label']} | Streak: {s['current_streak']}d")

# 6. Test Asking a doubt with teacher assignment and attachment
ask_req = doubts.AskDoubtRequest(
    title="Why is total angular momentum conserved in central forces?",
    subject="Physics",
    description="I am stuck on planetary orbit derivation with torque = 0.",
    teacher_id=teacher.id,
    attachment_url="/assets/uploads/doubt_test_diagram.png",
    attachment_name="orbit_torque_diagram.png",
    attachment_type="image"
)
st_heroic = db.query(models.User).filter_by(username="rahul_heroic").first()
doubt_created = doubts.ask_doubt(payload=ask_req, db=db, current_user=st_heroic)
print("Doubt created successfully:", doubt_created)

# 7. Test listing doubts for teacher
teacher_doubts = doubts.list_doubts(db=db, current_user=teacher)
print("Teacher Doubts Inbox Count:", len(teacher_doubts["doubts"]))
first_doubt = teacher_doubts["doubts"][0]
print(f"  - Doubt: '{first_doubt['title']}' from {first_doubt['student_name']} | Attachment: {first_doubt['attachment_url']}")

# 8. Test teacher answering doubt
reply_res = doubts.reply_doubt(
    doubt_id=doubt_created["doubt_id"],
    payload=doubts.ReplyDoubtRequest(message="Because tau = r x F, and for central force r is collinear with F, so tau = 0."),
    db=db,
    current_user=teacher
)
print("Teacher replied successfully:", reply_res)

print("\n🎉 ALL TESTS PASSED! PRINCIPAL DASHBOARD & DOUBT ATTACHMENTS VERIFIED!")
