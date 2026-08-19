# 🌟 EklavyaX

**EklavyaX** is a gamified AI learning platform for students and teachers, combining AI tutoring, virtual labs, assignments, progress tracking, and rewards.

## ✨ Features

**Student**
- 🤖 AI Tutor
- 🔬 Virtual Physics Labs
- 📈 Progress tracking
- 🏆 XP, EduCoins & streaks
- 🙋 Doubt solving
- 📝 Assignment submission

**Teacher**
- 📊 Student analytics
- 📚 Course management
- ✅ Assignment grading
- 💬 Doubt resolution
- 📢 Announcements

## 🛠️ Tech Stack
- **Frontend:** HTML, CSS, JS
- **Backend:** Python, FastAPI
- **Database:** SQLite / PostgreSQL
- **AI:** OpenRouter / Gemini / OpenAI
- **Auth:** JWT

## 🚀 Run Locally

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 🌐 URLs
- Website: http://localhost:8000
- Student: http://localhost:8000/student/student_login.html
- Teacher: http://localhost:8000/teacher/login.html
- API Docs: http://localhost:8000/docs

## 📁 Structure
```
eklavyax/
├── backend/
├── frontend/
└── README.md
```

## 🔑 Environment (`backend/.env`)
```
DATABASE_URL="sqlite:///./EklavyaX.db"
SECRET_KEY="your-secret-key"
AI_PROVIDER="openrouter"
OPENROUTER_API_KEY="your-api-key"
```

## 🧪 Testing
```bash
cd backend
python -m pytest tests/ -v
```

## 📄 License
MIT — Built with ❤️ for students and educators.
