# 🌟 EklavyaX — Next-Gen Gamified AI Learning Platform

<div align="center">

![EklavyaX Banner](frontend/assets/img/hero-illustration.svg)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite/PostgreSQL](https://img.shields.io/badge/Database-SQLite%20%7C%20Postgres-4169E1.svg?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![AI Models](https://img.shields.io/badge/AI%20Tutor-OpenRouter%20%7C%20Gemini%20%7C%20OpenAI-FF6F00.svg?style=for-the-badge&logo=google&logoColor=white)](https://openrouter.ai/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

**An intelligent, gamified educational ecosystem bridging pedagogy, AI mentoring, interactive virtual STEM labs, and peer incentive mechanics.**

[🚀 Quick Start](#-quick-start-guide) • [✨ Key Features](#-key-features) • [🏛️ Architecture](#-system-architecture) • [📡 API Reference](#-api-endpoints) • [⚙️ Configuration](#%EF%B8%8F-configuration--environment)

</div>

---

## 📖 Overview

**EklavyaX** re-imagines STEM education by combining **adaptive pedagogical AI tutoring**, **interactive physics/chemistry simulations**, and a **gamified economy** (EduCoins, XP, Levels, and Streaks). Built for both learners and educators, the platform provides real-time progress analytics, assignment grading workflows, and interactive doubt resolution.

---

## ✨ Key Features

### 🎓 Student Portal
- **⚡ AI Tutor & Concept Explainer (`Eklavya AI`)**: Multi-turn intelligent tutor powered by LLMs (OpenRouter, Gemini, OpenAI) that breaks down complex STEM concepts into intuitive analogies, formulas, and step-by-step solutions.
- **🔬 Interactive Virtual Lab**: Real-time interactive physics simulations (Pendulum Motion, Projectile Trajectory, Snell's Law Optics, Ohm's Law Circuit) with live parameters and visual canvas rendering.
- **📈 Dynamic Progress Tracking**: Interactive course curricula and syllabus tracker that dynamically updates lesson completion percentage, chapter statuses, and XP rewards.
- **🏆 Gamified Economy & Wallet**: Earn **EduCoins** and **XP** for completing lessons, maintaining daily streaks, solving peer bounties, and submitting assignments.
- **🙋 Doubts & Forum**: Raise academic doubts, tag subjects, filter answered vs. unresolved queries, and receive faculty feedback.
- **📝 Assignment Submissions**: View due dates, reward points, submit work, and review graded feedback.

### 👩‍🏫 Faculty / Teacher Portal
- **📊 Analytics & Student Progress**: Monitor class-wide performance, subject score distributions, and individual attendance trends via interactive Chart.js visualizations.
- **📚 Content & Curriculum Management**: Publish syllabus modules, study guides, video lessons, and interactive assignments with custom coin rewards.
- **✅ Assignment Grading Hub**: Review student submissions, assign percentage scores, and provide constructive feedback.
- **💬 Doubt Resolution Desk**: Direct access to student doubt queues with filtering by subject and real-time reply status.
- **📢 Broadcast Announcements**: Publish instant notices across classes with priority tags (Exam, Schedule, Event).

---

## 🏛️ System Architecture

```mermaid
graph TD
    subgraph Client["Frontend (Single Port Server)"]
        UI_Home["Landing Page (index.html)"]
        UI_Student["Student Dashboard & Labs"]
        UI_Teacher["Teacher Portal & Analytics"]
        API_JS["api.js / app_pages.js / student_courses.js"]
    end

    subgraph Backend["FastAPI Backend (Synapse.ai)"]
        Router["FastAPI Router & CORS Middleware"]
        AuthRoute["/auth (JWT, Streaks, Profile)"]
        EconRoute["/economy (Wallet, XP, Factions)"]
        BountyRoute["/bounties (Peer Bounties & Tasks)"]
        TutorRoute["/tutor (AI Explain & Mentoring)"]
    end

    subgraph Persistence["Data & AI Layer"]
        DB[(SQLite / PostgreSQL)]
        LLM["OpenRouter / Gemini / OpenAI APIs"]
    end

    UI_Student --> API_JS
    UI_Teacher --> API_JS
    API_JS --> Router
    Router --> AuthRoute
    Router --> EconRoute
    Router --> BountyRoute
    Router --> TutorRoute
    AuthRoute --> DB
    EconRoute --> DB
    BountyRoute --> DB
    TutorRoute --> LLM
```

---

## 🚀 Quick Start Guide

The backend serves the frontend statically on a single port—no CORS configuration or separate Node/Vite server required.

### 1. Prerequisites
- **Python 3.10+** installed on your system.
- Git (optional, for cloning).

### 2. Setup & Run

#### 💻 Windows (Command Prompt / PowerShell)
```powershell
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

#### 🐧 Linux / macOS / Git Bash
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

### 3. Open in Browser
| Destination | URL |
|---|---|
| 🏠 **Landing Page** | [http://localhost:8000](http://localhost:8000) |
| 🎓 **Student Portal** | [http://localhost:8000/student/student_login.html](http://localhost:8000/student/student_login.html) |
| 👩‍🏫 **Teacher Portal** | [http://localhost:8000/teacher/login.html](http://localhost:8000/teacher/login.html) |
| 📜 **Swagger Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| 📑 **ReDoc Alternative API Docs** | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

---

## 📂 Project Directory Structure

```
eklavyax/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py         # Registration, JWT login, profile sync, streaks
│   │   │       ├── bounties.py     # Bounty creation, solutions, peer rewards
│   │   │       ├── economy.py      # Wallet, EduCoin transactions, factions
│   │   │       └── tutor.py        # AI tutoring engine with OpenRouter/Gemini
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic environment settings
│   │   │   └── security.py     # Bcrypt password hashing & JWT token handling
│   │   ├── db/
│   │   │   ├── database.py     # SQLAlchemy engine & session factory
│   │   │   └── models.py       # User, Wallet, Bounty, Faction ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── main.py             # FastAPI entrypoint & frontend static mount
│   ├── tests/                  # Automated pytest test suites
│   ├── requirements.txt        # Backend dependencies
│   └── .env                    # Environment variables (API keys, DB config)
│
├── frontend/
│   ├── assets/                 # Fonts, branding logos, SVG illustrations, avatars
│   ├── css/                    # Modular stylesheets (Dark-mode, Glassmorphism)
│   │   ├── global.css          # Design tokens, variables & typography
│   │   ├── student_*.css       # Student UI styles
│   │   └── teacher_*.css       # Faculty portal styles
│   ├── js/
│   │   ├── api.js              # Fetch client communicating with backend
│   │   ├── app_pages.js        # Dynamic assignments, doubts, announcements & settings
│   │   ├── student_courses.js  # Course syllabus, lesson modal & progress engine
│   │   └── chatbot.js          # Live AI tutor floating widget
│   ├── student/                # Student portal pages (Dashboard, Lab, AI Tutor...)
│   ├── teacher/                # Teacher portal pages (Dashboard, MyClass, Doubts...)
│   └── index.html              # Marketing & platform landing page
└── README.md                   # Platform documentation
```

---

## 📡 API Endpoints

The backend provides a RESTful API with automated OpenAPI specifications:

### 🔐 Authentication & Profile (`/auth`)
- `POST /auth/register` — Register a new student or faculty account.
- `POST /auth/login` — Authenticate and receive a JWT Bearer token.
- `GET /auth/me` — Retrieve the current authenticated profile.
- `PUT /auth/me` — Update profile details (avatar, grade, bio, target exam).
- `GET /auth/me/streak` — Retrieve the current daily learning streak and multiplier.
- `POST /auth/me/activity` — Record daily learning activity to advance streak.

### 💰 Economy & Rewards (`/economy`)
- `GET /economy/wallet` — Check EduCoin balance, total XP, and current tier level.
- `GET /economy/leaderboard` — Global and class-wide XP leaderboard rankings.
- `GET /economy/factions` — View house/faction standings and member contributions.

### 🎯 Bounties & Tasks (`/bounties`)
- `GET /bounties` — List open peer doubt bounties and challenges.
- `POST /bounties` — Create a bounty with an EduCoin reward stake.
- `POST /bounties/{id}/claim` — Claim and submit a solution to an open bounty.

### 🤖 AI Tutor (`/tutor`)
- `POST /tutor/explain` — Get an interactive AI explanation, analogy, and step-by-step breakdown.
- `POST /tutor/chat` — Multi-turn academic conversation with contextual memory.

---

## ⚙️ Configuration & Environment

Configuration is managed via `backend/.env`. Copy `.env.example` or create `backend/.env`:

```env
# Application Settings
PROJECT_NAME="EklavyaX Synapse"
ENVIRONMENT="development"
DEBUG=True

# Database (Default: Zero-config SQLite)
DATABASE_URL="sqlite:///./EklavyaX.db"
# For PostgreSQL:
# DATABASE_URL="postgresql://user:password@localhost:5432/eklavyax"

# Security
SECRET_KEY="your-super-secret-jwt-key-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Provider Configuration
AI_PROVIDER="openrouter" # Options: "openrouter", "gemini", "openai"
OPENROUTER_API_KEY="sk-or-v1-..."
GEMINI_API_KEY=""
OPENAI_API_KEY=""
```

---

## 🧪 Testing

Execute automated unit and integration tests for the backend API:

```bash
cd backend
python -m pytest tests/ -v
```

---

## 🛡️ License & Acknowledgments

- Built with ❤️ for STEM learners and educators worldwide.
- Released under the **MIT License**. Feel free to fork, customize, and build upon EklavyaX!
