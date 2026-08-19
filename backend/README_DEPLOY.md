# EklavyaX — Deploy Guide

## Architecture

```
EklavyaX/
├── backend/          ← FastAPI app (serves BOTH the API and the frontend)
│   ├── app/
│   ├── requirements.txt
│   ├── Procfile      ← for Heroku / Railway / Render
│   ├── runtime.txt   ← Python 3.11
│   └── .env          ← secrets (DO NOT commit)
└── frontend/         ← Static HTML/CSS/JS (served by FastAPI at "/")
```

> The backend mounts the `../frontend` folder as static files at `/`.
> **Run only the backend** — it serves everything.

---

## Local Development

```powershell
# 1. Enter backend folder
cd EklavyaX\backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env     # then edit with your values

# 4. Start the server
uvicorn app.main:app --reload --port 8000

# 5. Open in browser
# http://localhost:8000          <- Full app (frontend + API)
# http://localhost:8000/docs     <- Swagger API docs
# http://localhost:8000/health   <- Health check
```

---

## Environment Variables (.env)

| Variable | Required | Description |
|---|---|---|
| DATABASE_URL | Yes | SQLite (default) or PostgreSQL URL |
| SECRET_KEY | Yes | Change in production — JWT signing key |
| AI_PROVIDER | Optional | openrouter (default), gemini, or openai |
| OPENROUTER_API_KEY | Optional | OpenRouter API key for AI Tutor feature |
| OPENROUTER_MODEL | Optional | OpenRouter model (default: google/gemini-2.0-flash-001) |
| GEMINI_API_KEY | Optional | Google AI key for fallback |
| CORS_ORIGINS | Optional | Comma-separated allowed origins |
| REDIS_URL | Optional | Redis for leaderboard caching |
| NEW_USER_COINS | Optional | Starting coins for new users (default: 100) |

### Production .env essentials
```
DATABASE_URL=postgresql://user:pass@host:5432/EklavyaX
SECRET_KEY=<random-64-char-string>
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=<your-openrouter-key>
OPENROUTER_MODEL=google/gemini-2.0-flash-001
APP_ENV=production
```

---

## Deploy to Railway (Recommended)

1. Push your repo to GitHub
2. Go to railway.app -> New Project -> Deploy from GitHub
3. Select root directory: EklavyaX/backend
4. Set environment variables in the Railway dashboard
5. Add a PostgreSQL plugin for the database
6. Railway auto-detects the Procfile and deploys

---

## Deploy to Render

1. Create a new Web Service on render.com
2. Root Directory: EklavyaX/backend
3. Build Command: pip install -r requirements.txt
4. Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
5. Set env vars in the Render dashboard
6. Add a PostgreSQL service and set DATABASE_URL

---

## Deploy to Heroku

```bash
cd EklavyaX/backend
heroku create EklavyaX-app
heroku addons:create heroku-postgresql:mini
heroku config:set SECRET_KEY="<your-secret>"
heroku config:set GEMINI_API_KEY="<your-key>"
heroku config:set APP_ENV=production
git subtree push --prefix EklavyaX/backend heroku main
```

---

## Post-Deploy Checklist

- Visit https://<your-domain>/health -> should return {"api":"ok"}
- Visit https://<your-domain>/docs -> Swagger UI loads
- Register a student account -> dashboard shows real coins/streak
- Register a teacher account -> dashboard shows real leaderboard
- Unauthenticated page access -> redirects to login
