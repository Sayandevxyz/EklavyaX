# EklavyaX — Full Stack

A working full-stack build: the original EklavyaX frontend wired up to a real Node/Express
backend with JWT authentication, a student dashboard API, and a teacher analytics API.

## Stack

- **Backend:** Node.js, Express, JWT auth (`jsonwebtoken`), password hashing (`bcryptjs`)
- **Data store:** a JSON file (`data/db.json`) via a tiny read/write module — no native
  dependencies to compile, no external database to install. Swap in Postgres/Mongo later by
  replacing `src/db.js` without touching the routes.
- **Frontend:** the original static `index.html` / `login.html` / `style.css`, with `script.js`
  updated to call the real API instead of faking the login.

## Project layout

```
EklavyaX-fullstack/
├── server.js              # Express app entry point (serves API + static frontend)
├── package.json
├── .env.example
├── data/
│   └── db.json             # auto-created & seeded on first run
├── src/
│   ├── db.js                # JSON file read/write helpers
│   ├── middleware/auth.js   # JWT verification + role guard
│   ├── routes/
│   │   ├── auth.js          # POST /api/auth/register, /api/auth/login
│   │   ├── dashboard.js     # GET/POST /api/dashboard/... (student)
│   │   └── teacher.js       # GET /api/teacher/students (teacher)
│   └── utils/seed.js        # creates demo users, lessons, dashboard stats
└── public/
    ├── index.html
    ├── login.html
    ├── style.css
    └── script.js
```

## Run it

```bash
cd EklavyaX-fullstack
npm install
cp .env.example .env      # optional — edit JWT_SECRET for anything beyond local demo use
npm start
```

Then open **http://localhost:4000**. The database is auto-seeded the first time you start the
server, so login works immediately — no separate setup step required.

To reseed from scratch at any point (this overwrites `data/db.json`):

```bash
npm run seed
```

## Demo accounts

All seeded accounts use the password `password123`.

| Role    | Email                  | Notes                          |
|---------|-------------------------|--------------------------------|
| Student | arjun@EklavyaX.com     | Level 12, 14-day streak        |
| Student | anika@EklavyaX.com     | Level 9                        |
| Student | rishi@EklavyaX.com     | Level 15, close to leveling up |
| Student | meera@EklavyaX.com     | Low accuracy — flagged "at risk" |
| Teacher | kavitha@EklavyaX.com   | Sees the full student roster   |

Sign in on the Student tab with any student account and the landing-page dashboard preview
switches from static placeholder numbers to your real data pulled from `/api/dashboard/me`.

## API reference

All authenticated endpoints expect `Authorization: Bearer <token>`.

### `POST /api/auth/register`
Body: `{ name, email, password, role }` (`role` is `"student"` or `"teacher"`)
Returns: `{ token, user }`

### `POST /api/auth/login`
Body: `{ email, password, role? }`
Returns: `{ token, user }`

### `GET /api/dashboard/me` (student)
Returns the current student's level, XP, coins, streak, accuracy, and in-progress lesson.

### `POST /api/dashboard/progress` (student)
Body: `{ xpGained?, lessonProgress? }`
Applies XP (auto-leveling when the XP threshold is crossed) and/or updates lesson progress.

### `GET /api/teacher/students` (teacher)
Returns the class roster with an `atRisk` flag (low accuracy or a broken streak) per student,
plus class-wide averages.

### `GET /api/health`
Simple liveness check.

## Notes

- Fonts (Space Grotesk + Inter) load from Google Fonts — an internet connection is needed for
  those to render; everything else works offline once dependencies are installed.
- The JWT secret in `.env.example` is a placeholder — set a real random string in `.env` before
  using this anywhere beyond local development.
- `data/db.json` is a flat-file store meant for demoing the full request/response flow end to
  end. For production use, replace `src/db.js` with a real database client — the routes don't
  need to change since they only call `read()`/`write()`.
- Virtual coins/XP have no real monetary value (carried over from the original frontend footer).
