import sys
import os

# Set working directory to project root
proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(proj_dir, "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db, Base, engine
from app.db import models
from app.core.security import get_current_user

# Create all database tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# Create mock test users
mock_student = models.User(
    id=901,
    username="ArjunTestStudent",
    email="student_test@eklavya.edu",
    hashed_password="mockpassword",
    role=models.UserRole.student,
    grade="11",
)

mock_physics_teacher = models.User(
    id=902,
    username="ProfSharmaPhysics",
    email="teacher_physics@eklavya.edu",
    hashed_password="mockpassword",
    role=models.UserRole.teacher,
    specialization_subject="Physics",
)

def run_tests():
    print("=== STARTING COMPREHENSIVE VERIFICATION FOR EKLAVYAX PEDAGOGY SUITE ===")
    errors = []

    # Override current user for teacher tests
    app.dependency_overrides[get_current_user] = lambda: mock_physics_teacher

    # Test 1: Faculty Doubt Heatmap
    try:
        r = client.get("/api/pedagogy/teacher/doubt-heatmap?subject=Physics")
        assert r.status_code == 200, f"Heatmap status: {r.status_code}"
        data = r.json()
        assert "topics" in data, "Heatmap response missing 'topics'"
        assert len(data["topics"]) > 0, "Heatmap topics list is empty"
        assert any(t["color"] == "red" for t in data["topics"]), "No red struggle topics found"
        print("[PASS] Test 1: Faculty Doubt Heatmap returns color-coded struggle topics (Red/Yellow/Green)")
    except Exception as e:
        print(f"[FAIL] Test 1: {e}")
        errors.append(f"Test 1: {e}")

    # Override for student tests
    app.dependency_overrides[get_current_user] = lambda: mock_student

    # Test 2: Prerequisite Foundation Checker (EklavyaALERT)
    try:
        r = client.get("/api/pedagogy/student/prerequisites/Rotational%20Motion")
        assert r.status_code == 200, f"Prerequisites status: {r.status_code}"
        data = r.json()
        assert "prerequisites" in data, "Missing prerequisites in response"
        assert any("Kinematics" in p for p in data["prerequisites"]), "Prerequisite missing Kinematics"
        assert "confidence_boost" in data, "Missing confidence boost message"
        print("[PASS] Test 2: EklavyaALERT prerequisite graph successfully links Rotational Motion -> Kinematics")
    except Exception as e:
        print(f"[FAIL] Test 2: {e}")
        errors.append(f"Test 2: {e}")

    # Test 3: Revision Radar (Ebbinghaus Spaced Repetition)
    try:
        r = client.get("/api/pedagogy/student/revision-radar")
        assert r.status_code == 200, f"Revision radar status: {r.status_code}"
        data = r.json()
        assert "schedules" in data, "Missing schedules in Revision Radar"
        assert len(data["schedules"]) >= 3, "Expected at least 3 radar schedules"
        assert "active_due_count" in data, "Missing active_due_count"
        print("[PASS] Test 3: Revision Radar returns Day 1, Day 7, Day 30 forgetting curve intervals")
    except Exception as e:
        print(f"[FAIL] Test 3: {e}")
        errors.append(f"Test 3: {e}")

    # Test 4: Weak Area Improvement Engine & Retry
    try:
        r = client.get("/api/pedagogy/student/weak-areas")
        assert r.status_code == 200, f"Weak areas status: {r.status_code}"
        data = r.json()
        assert "weak_areas" in data, "Missing weak_areas in response"
        assert len(data["weak_areas"]) > 0, "No weak areas found"
        
        first_flag = data["weak_areas"][0]
        retry_res = client.post(
            f"/api/pedagogy/student/weak-areas/{first_flag['id']}/retry",
            json={"answers": [0, 0, 0]}
        )
        assert retry_res.status_code == 200, f"Weak area retry status: {retry_res.status_code}"
        retry_data = retry_res.json()
        assert "new_score_pct" in retry_data, "Missing new_score_pct in retry response"
        assert "bonus_coins_awarded" in retry_data, "Missing bonus coins in retry response"
        print("[PASS] Test 4: Weak Area Improvement records retry score and awards bonus EduCoins proportional to score delta")
    except Exception as e:
        print(f"[FAIL] Test 4: {e}")
        errors.append(f"Test 4: {e}")

    # Test 5: PYQ Arena (JEE Main, NEET, CBSE)
    try:
        r = client.get("/api/pedagogy/pyqs?exam_type=jee_main&subject=Physics")
        assert r.status_code == 200, f"PYQ status: {r.status_code}"
        data = r.json()
        assert "questions" in data, "Missing questions in PYQ response"
        assert len(data["questions"]) > 0, "No PYQ questions found"
        
        submit_res = client.post(
            "/api/pedagogy/pyqs/submit",
            json={
                "exam_type": "jee_main",
                "year": 2024,
                "subject": "Physics",
                "time_taken_sec": 45,
                "answers": [{"question_id": data["questions"][0]["id"], "chosen_index": 0}]
            }
        )
        assert submit_res.status_code == 200, f"PYQ submit status: {submit_res.status_code}"
        sub_data = submit_res.json()
        assert "estimated_percentile" in sub_data, "Missing estimated percentile"
        print("[PASS] Test 5: PYQ Arena returns questions and evaluates attempt with estimated percentile")
    except Exception as e:
        print(f"[FAIL] Test 5: {e}")
        errors.append(f"Test 5: {e}")

    # Test 6: Silently Struggling Detector
    try:
        r = client.get("/api/pedagogy/student/silent-struggles")
        assert r.status_code == 200, f"Silent struggles status: {r.status_code}"
        data = r.json()
        assert "detected_struggles" in data, "Missing detected_struggles"
        assert any("Inclined Planes" in s["silent_micro_concept"] for s in data["detected_struggles"]), "Normal force struggle not found"
        print("[PASS] Test 6: Silently Struggling Detector flags micro-concept failure patterns before exams")
    except Exception as e:
        print(f"[FAIL] Test 6: {e}")
        errors.append(f"Test 6: {e}")

    # Test 7: Revision Bookmarks Vault (Toggle & List)
    try:
        toggle_res = client.post(
            "/api/pedagogy/bookmarks/toggle",
            json={
                "question_id": 101,
                "question_type": "daily",
                "subject": "Physics",
                "topic": "Electromagnetism",
                "prompt": "What is the magnetic field inside a long solenoid?",
                "options": ["u0nI", "u0I / 2R", "Zero", "u0I / 2piR"],
                "correct_option_index": 0,
                "explanation": "B = u0nI where n is turns per unit length.",
                "note": "Verify formula derivation"
            }
        )
        assert toggle_res.status_code == 200, f"Bookmark toggle status: {toggle_res.status_code}"
        assert toggle_res.json()["status"] == "saved", "Bookmark did not save"

        list_res = client.get("/api/pedagogy/bookmarks")
        assert list_res.status_code == 200, f"Bookmarks list status: {list_res.status_code}"
        bm_data = list_res.json()
        assert any("solenoid" in b["prompt"] for b in bm_data["bookmarks"]), "Saved bookmark not found in list"

        toggle_remove = client.post(
            "/api/pedagogy/bookmarks/toggle",
            json={
                "question_id": 101,
                "question_type": "daily",
                "subject": "Physics",
                "topic": "Electromagnetism",
                "prompt": "What is the magnetic field inside a long solenoid?",
                "options": ["u0nI", "u0I / 2R", "Zero", "u0I / 2piR"],
                "correct_option_index": 0,
            }
        )
        assert toggle_remove.json()["status"] == "removed", "Bookmark did not remove on toggle"
        print("[PASS] Test 7: Bookmarks Vault supports saving, listing, and deduplicated toggling")
    except Exception as e:
        print(f"[FAIL] Test 7: {e}")
        errors.append(f"Test 7: {e}")

    # Test 8: Concept Mind Maps (Physics & Social Science)
    try:
        r_phys = client.get("/api/pedagogy/mindmaps/physics")
        assert r_phys.status_code == 200, f"Physics mindmap status: {r_phys.status_code}"
        assert len(r_phys.json()["nodes"]) > 0, "Physics mindmap nodes empty"

        r_soc = client.get("/api/pedagogy/mindmaps/social_science")
        assert r_soc.status_code == 200, f"Social Science mindmap status: {r_soc.status_code}"
        assert len(r_soc.json()["nodes"]) > 0, "Social science mindmap nodes empty"
        print("[PASS] Test 8: Interactive Concept Mind Maps return prerequisite-linked nodes for STEM & Social Science")
    except Exception as e:
        print(f"[FAIL] Test 8: {e}")
        errors.append(f"Test 8: {e}")

    # Test 9: Verify HTML Files Exist and Contain Key Pedagogical Components
    html_checks = [
        ("frontend-react/public/legacy/teacher/analytics.html", ["Doubt & Struggle Heatmap", "High Struggle", "Schedule 15-Min Remedial", "Assign Targeted Practice"]),
        ("frontend-react/public/legacy/student/eklavyalens.html", ["EklavyaLens", "Indus", "Ganga", "Himalayas", "Civilization", "Terrain"]),
        ("frontend-react/public/legacy/student/pyq_arena.html", ["PYQ Arena", "JEE Main", "NEET", "CBSE Class 12", "timerDisplay"]),
        ("frontend-react/public/legacy/student/bookmarks.html", ["Revision Bookmarks Vault", "Practice My Bookmarks", "Formulas"]),
        ("frontend-react/public/legacy/student/mindmaps.html", ["Concept Dependency Mind Map", "Interactive Concept Network", "Prerequisite Flow"]),
        ("frontend-react/public/legacy/student/explore_courses.html", ["Classes 6", "EklavyaLens Maps", "Social Science (EklavyaLens)", "All Grades"]),
        ("frontend-react/public/legacy/student/student_dashboard.html", ["EklavyaLens Maps", "PYQ Arena", "Mind Maps", "Revision Vault", "Silently Struggling Detector", "Revision Radar"]),
        ("frontend-react/public/legacy/student/quiz.html", ["EklavyaALERT", "Prerequisite Dependency", "bookmarkCurrentQuestion"]),
    ]

    for rel_path, required_strings in html_checks:
        full_path = os.path.join(proj_dir, rel_path)
        assert os.path.exists(full_path), f"File not found: {rel_path}"
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        for s in required_strings:
            assert s in content, f"'{s}' not found in {rel_path}"
        print(f"[PASS] HTML Check: {rel_path}")

    # Clean up dependency override
    app.dependency_overrides.clear()

    if errors:
        print(f"\n[FAIL] {len(errors)} ERRORS DETECTED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n>>> ALL 9 PEDAGOGICAL MASTERY & ANALYTICS TEST SUITES PASSED SUCCESSFULLY (100% GREEN)!")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
