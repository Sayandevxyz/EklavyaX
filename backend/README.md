# 🎓 EklavyaX — Synapse Backend

> **EklavyaX** is a gamified learning platform inspired by the legendary self-taught archer of Indian mythology. The `X` signals a cutting-edge, tech-enabled evolution of self-learning.
>
> Powered by **Synapse.ai** — a custom-prompted AI explanation engine that acts as an empathetic tutor, never just an answer machine.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔥 **Streak Engine** | Daily learning streaks with freeze tokens (Duolingo-style loss aversion) |
| 💰 **Virtual Economy** | EduCoins wallet, full transaction ledger, earn/spend/refund mechanics |
| 🏰 **Faction Wars** | Students sorted into 4 Houses; XP contributes to faction score |
| ⚔️ **Peer Challenges** | 1v1 battles with optional EduCoin wagers ("Double or Nothing") |
| 📋 **Bounty Board** | Teachers post timed challenges; students claim rewards on completion |
| 🤖 **Synapse.ai** | AI-powered "Highlight & Explain" feature with gamified coin cost + refund |
| 🏆 **Leaderboards** | Class XP rankings + Faction War standings |
| 🔐 **JWT Auth** | Secure registration/login with role-based access (student/teacher/admin) |

---

## 🏗️ Project Structure

```
synapse-backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py        # Register, Login, Profile, Streak activity
│   │       ├── bounties.py    # Teacher Bounty Board
│   │       ├── economy.py     # Wallet, Challenges, Leaderboards
│   │       └── tutor.py       # Synapse.ai Explain + Feedback
│   ├── core/
│   │   ├── config.py          # Pydantic settings (env vars)
│   │   └── security.py        # bcrypt + JWT utilities
│   ├── db/
│   │   ├── database.py        # SQLAlchemy engine + get_db dependency
│   │   └── models.py          # All ORM models (SQLAlchemy 2.0)
│   ├── schemas/
│   │   ├── user_sch.py
│   │   ├── bounty_sch.py
│   │   ├── economy_sch.py
│   │   └── tutor_sch.py
│   ├── services/
│   │   ├── ai_service.py      # Gemini / OpenAI API calls + prompt engineering
│   │   └── game_logic.py      # Streak, wallet, faction, leaderboard algorithms
│   └── main.py                # FastAPI app factory + startup lifecycle
├── tests/
│   └── test_core.py           # pytest unit tests (SQLite in-memory)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/your-org/EklavyaX-synapse-backend.git
cd EklavyaX-synapse-backend/synapse-backend
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your actual values (DB URL, API keys, etc.)
```

### 5. Set up PostgreSQL database
```sql
CREATE DATABASE EklavyaX;
```

### 6. Run the development server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## 🌐 API Endpoints

### Authentication
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | Public | Create account, assign faction, init wallet |
| `POST` | `/auth/login` | Public | Get JWT token |
| `GET` | `/auth/me` | Any | Current user profile |
| `GET` | `/auth/me/streak` | Any | Current streak data |
| `POST` | `/auth/me/activity` | Any | Record learning activity (updates streak) |

### Bounty Board
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `POST` | `/bounties` | Teacher | Create a new bounty |
| `GET` | `/bounties` | Any | List active bounties |
| `POST` | `/bounties/{id}/submit` | Student | Submit bounty completion claim |
| `POST` | `/bounties/{id}/approve` | Teacher | Approve/reject submission + award coins |
| `GET` | `/bounties/{id}/submissions` | Teacher | View all submissions for a bounty |

### Economy & Challenges
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `GET` | `/economy/wallet` | Any | EduCoin balance + XP |
| `GET` | `/economy/transactions` | Any | Transaction history |
| `POST` | `/economy/earn` | Admin/Teacher | Manually award coins/XP |
| `POST` | `/economy/spend` | Any | Deduct coins |
| `POST` | `/challenges` | Student | Create peer challenge (+ wager) |
| `POST` | `/challenges/{id}/accept` | Student | Accept a challenge |
| `POST` | `/challenges/{id}/submit` | Student | Submit result → transfer wager to winner |
| `GET` | `/challenges` | Any | List user's challenges |
| `GET` | `/leaderboard/class` | Any | Top 10 students by XP |
| `GET` | `/leaderboard/faction` | Any | Faction war standings |

### Synapse.ai Tutor
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `POST` | `/tutor/explain` | Student | AI explanation (costs EduCoins) |
| `POST` | `/tutor/answer-feedback` | Student | Correct answer → coin refund |
| `GET` | `/tutor/history` | Any | View past AI explanations |

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | — | JWT signing key (min 32 chars) |
| `ALGORITHM` | | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `60` | Token lifetime |
| `AI_PROVIDER` | | `openrouter` | `openrouter`, `gemini`, or `openai` |
| `OPENROUTER_API_KEY` | ✅* | — | OpenRouter API key |
| `OPENROUTER_MODEL` | | `google/gemini-2.0-flash-001` | OpenRouter model identifier |
| `GEMINI_API_KEY` | Optional | — | Google AI Studio API key |
| `GEMINI_MODEL` | | `gemini-1.5-flash` | Gemini model name |
| `OPENAI_API_KEY` | Optional | — | OpenAI API key |
| `OPENAI_MODEL` | | `gpt-4o-mini` | OpenAI model name |
| `AI_EXPLAIN_COST` | | `10` | EduCoins per AI explain call |
| `AI_REFUND_COINS` | | `5` | Coins refunded on correct answer |
| `STREAK_BONUS_COINS` | | `5` | Daily streak coin reward |
| `STREAK_BONUS_XP` | | `10` | Daily streak XP reward |
| `NEW_USER_COINS` | | `100` | Starting wallet balance |
| `CORS_ORIGINS` | | `localhost:3000` | Comma-separated allowed origins |
| `REDIS_URL` | | — | Optional Redis URL for caching |

> *Only the key for your chosen `AI_PROVIDER` is required.

---

## 🧪 Running Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with coverage
pip install pytest-cov
pytest tests/ -v --cov=app --cov-report=html
```

Tests use **SQLite in-memory** database — no PostgreSQL needed.

### Test Coverage
- ✅ Password hashing and verification (bcrypt)
- ✅ JWT creation, decoding, and expiry
- ✅ Faction assignment and balancing
- ✅ Streak logic (first activity, same day, consecutive, gap + freeze, reset)
- ✅ Wallet earn / spend / refund
- ✅ Transaction ledger recording
- ✅ AI prompt builder output
- ✅ OpenRouter / Multi-provider AI dispatch

---

## 🤖 Obtaining API Keys

### OpenRouter (Default / Recommended)
1. Visit [OpenRouter Keys](https://openrouter.ai/keys)
2. Sign in or create an account
3. Click **"Create Key"**
4. Copy the key to `OPENROUTER_API_KEY` in your `.env`
5. (Optional) Customize `OPENROUTER_MODEL` to your preferred model (e.g. `google/gemini-2.0-flash-001`, `meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-chat`)

### Google Gemini
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy the key to `GEMINI_API_KEY` in your `.env` and set `AI_PROVIDER=gemini`

### OpenAI
1. Visit [platform.openai.com](https://platform.openai.com/api-keys)
2. Create an account and add a payment method
3. Generate an API key
4. Copy to `OPENAI_API_KEY` in your `.env` and set `AI_PROVIDER=openai`

---

## 🏛️ The Synapse.ai Flow (Highlight & Explain)

```
Student highlights text
        ↓
Frontend calls POST /tutor/explain
        ↓
Backend checks balance ≥ AI_EXPLAIN_COST (10 coins)
        ↓
Deduct coins from wallet
        ↓
Build empathetic tutor prompt (NEVER gives direct answer)
        ↓
Call Gemini / OpenAI API
        ↓
Log to AIExplanationLog table
        ↓
Return explanation + new_balance + log_id
        ↓
Student reads explanation → answers question
        ↓
Frontend calls POST /tutor/answer-feedback {correct: true}
        ↓
Backend refunds AI_REFUND_COINS (5 coins) — "Good Student" reward
```

---

## 🎮 Gamification Economy

```
Actions that EARN coins:
  +100  Welcome bonus (on registration)
  +5    Daily streak bonus
  +N    Bounty reward (set by teacher)
  +Pot  Challenge wager win
  +5    AI refund (correct answer after using Synapse.ai)

Actions that SPEND coins:
  -10   AI Explain (Synapse.ai)
  -N    Challenge wager
```

---

## 🏰 The Four Factions

| House | Element | Color | Description |
|-------|---------|-------|-------------|
| **Vidyut** | Lightning | 🔵 Blue | Masters of logic — swift thinkers |
| **Agni** | Fire | 🔴 Red | Fearless pioneers — lead from the front |
| **Vayu** | Wind | 🟢 Green | Fleet-footed scholars — driven by curiosity |
| **Prithvi** | Earth | 🟡 Amber | Steadfast protectors — depth moves mountains |

---

## 📈 Scalability Notes

- **Connection Pooling**: SQLAlchemy is configured with `pool_size=10`, `max_overflow=20`.
- **Redis Caching**: Set `REDIS_URL` to cache leaderboards and reduce DB load.
- **Async AI Calls**: The `/tutor/explain` endpoint uses `async/await` for non-blocking AI API calls.
- **N+1 Prevention**: Leaderboard queries use JOINs rather than lazy-loading.

---

## 📄 License

MIT License — built for EklavyaX (SIH 2024 Hackathon)
