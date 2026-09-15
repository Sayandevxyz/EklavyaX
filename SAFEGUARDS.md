# EklavyaX Anti-Gaming Safeguards

## Overview

All quiz and reward paths are gated by a server-side validation pipeline in
`backend/app/services/safeguards.py`. The system is **fail-safe**: if any check
encounters an internal error, the reward is **rejected** rather than granted.

---

## Implemented Safeguards

| # | Safeguard | Status | Config Key |
|---|-----------|--------|------------|
| 1 | **Server-side answer validation** — client never determines correctness. Answers are shuffled per session and validated against server answer key. | ✅ Implemented | — |
| 2 | **Per-question cooldown** — rejects answers submitted faster than threshold using server-recorded `question_shown_at` timestamp. | ✅ Implemented | `QUESTION_MIN_COOLDOWN_SECONDS` (default 2.0) |
| 3 | **Daily earn caps** — maximum coins and XP per day, with configurable policy on cap exceeded. | ✅ Implemented | `DAILY_MAX_COINS` (500), `DAILY_MAX_XP` (1000), `CAP_EXCEEDED_POLICY` ("reject" / "zero" / "reduced"), `CAP_REDUCTION_FACTOR` (0.25) |
| 4 | **Suspicious pattern flagging** — rolling z-score analysis of response time and accuracy. Flags (does NOT block) outlier accounts for review. | ✅ Implemented | `ROLLING_WINDOW_SIZE` (20), `Z_SCORE_FLAG_THRESHOLD` (2.5) |
| 5 | **Queryable audit log** — every grant, rejection, and flag is logged with structured reason codes. | ✅ Implemented | — |
| 6 | **Answer option shuffling** — options randomised per session so cached "correct = B" exploits fail. | ✅ Implemented | — |
| 7 | **Fail-safe error handling** — any internal error in the pipeline rejects the reward and logs the failure. | ✅ Implemented | — |

---

## Reason Codes (in `reward_audit_logs`)

| Code | Meaning |
|------|---------|
| `granted` | Reward successfully granted after all checks passed |
| `cooldown_violation` | Answer submitted too quickly after question was shown |
| `cap_exceeded` | Daily coin/XP cap reached; reward reduced or rejected |
| `pattern_flagged` | User's response pattern is a statistical outlier (flag only) |
| `invalid_answer` | Wrong answer selected, or internal error (fail-safe) |

---

## Pipeline Execution Order

```
1. validate_server_answer()  →  reject if wrong answer
2. check_question_cooldown() →  reject if < min cooldown
3. check_and_apply_daily_cap() → adjust/reject if cap exceeded
4. grant reward + write audit log
5. evaluate_suspicious_patterns() (async, non-blocking)
```

---

## What Is NOT In Scope (Manual / Planned)

| Item | Status |
|------|--------|
| **Automated banning** | ❌ Not implemented. Flagging only — human review required. |
| **IP-based rate limiting** | ❌ Not implemented. Can be added via middleware later. |
| **CAPTCHA on suspicious accounts** | ❌ Not implemented. Planned for future. |
| **Admin review dashboard** | ❌ Not implemented. Audit logs are queryable via SQL / API. |
| **Multi-device session detection** | ❌ Not implemented. |

---

## Configuration

All thresholds are in `backend/app/core/config.py` under the `Settings` class
and can be overridden via environment variables or `.env` file.
