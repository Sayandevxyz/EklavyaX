from __future__ import annotations

import logging
import math
import random
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.services.game_logic import earn_coins_and_xp

logger = logging.getLogger(__name__)




def generate_shuffled_options(
    question: models.QuizQuestion,
) -> Tuple[List[str], List[int]]:
    """
    Randomise the option order for a question.

    Returns:
        (shuffled_options, permutation)
        permutation[i] = canonical index that is now at position i.
        e.g. permutation = [2, 0, 3, 1] means position 0 shows canonical option 2.
    """
    canonical = question.get_canonical_options()
    indices = list(range(len(canonical)))
    random.shuffle(indices)
    shuffled = [canonical[i] for i in indices]
    return shuffled, indices


def permutation_to_str(perm: List[int]) -> str:
    """Serialise a permutation list to a comma-separated string."""
    return ",".join(str(i) for i in perm)


def str_to_permutation(s: str) -> List[int]:
    """Deserialise a comma-separated permutation string."""
    return [int(x) for x in s.split(",")]


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime has UTC timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)



def validate_server_answer(
    session: models.QuizSession,
    selected_shuffled_index: int,
) -> bool:
    """
    Map the client's selected index (in shuffled order) back to the canonical
    index and compare with the question's correct_option_index.

    The client NEVER determines correctness; this function is the sole arbiter.

    Returns:
        True if the answer is correct.
    """
    perm = str_to_permutation(session.shuffled_order)
    if selected_shuffled_index < 0 or selected_shuffled_index >= len(perm):
        return False
    canonical_index = perm[selected_shuffled_index]
    return canonical_index == session.question.correct_option_index




def check_question_cooldown(
    session: models.QuizSession,
    submitted_at: datetime,
) -> Optional[str]:
    """
    Reject answers submitted faster than QUESTION_MIN_COOLDOWN_SECONDS
    after question_shown_at (server-recorded timestamp).

    Returns:
        None if OK, or a rejection detail string.
    """
    t_sub = ensure_utc(submitted_at)
    t_show = ensure_utc(session.question_shown_at)
    elapsed = (t_sub - t_show).total_seconds()
    if elapsed < settings.QUESTION_MIN_COOLDOWN_SECONDS:
        return (
            f"Answer submitted in {elapsed:.1f}s, minimum is "
            f"{settings.QUESTION_MIN_COOLDOWN_SECONDS}s"
        )
    return None



def _get_today_earned(db: Session, user_id: int) -> Tuple[int, int]:
    """
    Sum coins and XP earned today (UTC) via quiz rewards (reason_code = granted).
    """
    today_utc_str = datetime.now(timezone.utc).date().isoformat()
    row = (
        db.query(
            func.coalesce(func.sum(models.RewardAuditLog.reward_coins), 0).label("coins"),
            func.coalesce(func.sum(models.RewardAuditLog.reward_xp), 0).label("xp"),
        )
        .filter(
            models.RewardAuditLog.user_id == user_id,
            models.RewardAuditLog.reason_code == models.ReasonCode.granted,
            func.date(models.RewardAuditLog.created_at) >= today_utc_str,
        )
        .one()
    )
    return int(row.coins), int(row.xp)


def check_and_apply_daily_cap(
    db: Session,
    user_id: int,
    requested_coins: int,
    requested_xp: int,
) -> Tuple[int, int, Optional[str]]:
    """
    Enforce daily earn caps. Returns the (adjusted_coins, adjusted_xp, detail).
    detail is None if no cap was hit; otherwise describes what happened.

    Behaviour is controlled by CAP_EXCEEDED_POLICY:
      - "reject"  → 0, 0, reason
      - "zero"    → 0, 0, reason
      - "reduced" → coins * factor, xp * factor, reason
    """
    earned_coins, earned_xp = _get_today_earned(db, user_id)

    coins_headroom = max(0, settings.DAILY_MAX_COINS - earned_coins)
    xp_headroom = max(0, settings.DAILY_MAX_XP - earned_xp)

    if requested_coins <= coins_headroom and requested_xp <= xp_headroom:
        return requested_coins, requested_xp, None

    # Cap exceeded
    policy = settings.CAP_EXCEEDED_POLICY.lower()
    detail = (
        f"Daily cap hit: earned {earned_coins}/{settings.DAILY_MAX_COINS} coins, "
        f"{earned_xp}/{settings.DAILY_MAX_XP} XP today. Policy: {policy}"
    )

    if policy == "reject":
        return 0, 0, detail
    elif policy == "zero":
        return 0, 0, detail
    else:  # "reduced"
        factor = settings.CAP_REDUCTION_FACTOR
        adj_coins = min(int(requested_coins * factor), coins_headroom)
        adj_xp = min(int(requested_xp * factor), xp_headroom)
        return adj_coins, adj_xp, detail



def _write_audit_log(
    db: Session,
    user_id: int,
    question_id: Optional[str],
    coins: int,
    xp: int,
    reason_code: models.ReasonCode,
    is_flagged: bool = False,
    details: Optional[str] = None,
) -> models.RewardAuditLog:
    """Write a single row to reward_audit_logs."""
    log = models.RewardAuditLog(
        user_id=user_id,
        question_id=question_id,
        reward_coins=coins,
        reward_xp=xp,
        reason_code=reason_code,
        is_flagged=is_flagged,
        details=details,
    )
    db.add(log)
    return log




def evaluate_suspicious_patterns(
    db: Session,
    user_id: int,
    response_time_ms: int,
    is_correct: bool,
    question_id: int,
) -> bool:
    """
    Compute rolling z-scores for response time and accuracy.
    If the user's profile is a statistical outlier, FLAG (don't block)
    by writing to reward_audit_logs with reason_code=pattern_flagged.

    Returns True if the user was flagged.
    """
    try:

        metric = models.UserResponseMetric(
            user_id=user_id,
            question_id=question_id,
            response_time_ms=response_time_ms,
            is_correct=is_correct,
        )
        db.add(metric)
        db.flush()

        window = settings.ROLLING_WINDOW_SIZE
        recent = (
            db.query(models.UserResponseMetric)
            .filter_by(user_id=user_id)
            .order_by(models.UserResponseMetric.created_at.desc())
            .limit(window)
            .all()
        )

        if len(recent) < 5:
            
            return False

        times = [m.response_time_ms for m in recent]
        correct_count = sum(1 for m in recent if m.is_correct)
        accuracy = correct_count / len(recent)

        
        mean_time = sum(times) / len(times)
        if len(times) > 1:
            variance = sum((t - mean_time) ** 2 for t in times) / (len(times) - 1)
            std_time = math.sqrt(variance) if variance > 0 else 1.0
        else:
            std_time = 1.0

        z_speed = (mean_time - response_time_ms) / std_time if std_time > 0 else 0
       

       
        threshold = settings.Z_SCORE_FLAG_THRESHOLD
        flagged = z_speed > threshold and accuracy > 0.9

        if flagged:
            _write_audit_log(
                db,
                user_id=user_id,
                question_id=str(question_id),
                coins=0,
                xp=0,
                reason_code=models.ReasonCode.pattern_flagged,
                is_flagged=True,
                details=(
                    f"Speed z-score={z_speed:.2f} (threshold={threshold}), "
                    f"accuracy={accuracy:.0%} over last {len(recent)} questions"
                ),
            )
            db.commit()
            logger.warning(
                "⚠️ Pattern flag: user %d speed_z=%.2f accuracy=%.0f%%",
                user_id, z_speed, accuracy * 100,
            )

        return flagged

    except Exception as exc:
        logger.error("Pattern evaluation failed for user %d: %s", user_id, exc)
        return False




def _update_battle_contribution(
    db: Session,
    user_id: int,
    faction_id: int,
    xp: int,
) -> None:
    """
    If there is an active faction battle, credit the XP to the faction's
    battle score and the user's individual contribution.
    """
    now = datetime.now(timezone.utc)
    all_battles = (
        db.query(models.FactionBattle)
        .filter(models.FactionBattle.status == models.BattleStatus.active)
        .all()
    )
    battle = None
    for b in all_battles:
        start_utc = ensure_utc(b.start_time)
        end_utc = ensure_utc(b.end_time)
        if start_utc and end_utc and start_utc <= now <= end_utc:
            battle = b
            break

    if not battle:
        return

    fscore = (
        db.query(models.FactionBattleScore)
        .filter_by(battle_id=battle.id, faction_id=faction_id)
        .first()
    )
    if not fscore:
        fscore = models.FactionBattleScore(
            battle_id=battle.id,
            faction_id=faction_id,
        )
        db.add(fscore)
        db.flush()
    fscore.total_xp += xp
    fscore.contributor_count = (
        db.query(func.count(models.FactionBattleContribution.id))
        .filter_by(battle_id=battle.id, faction_id=faction_id)
        .scalar() or 0
    ) + 1  


    contrib = (
        db.query(models.FactionBattleContribution)
        .filter_by(battle_id=battle.id, user_id=user_id)
        .first()
    )
    if not contrib:
        contrib = models.FactionBattleContribution(
            battle_id=battle.id,
            user_id=user_id,
            faction_id=faction_id,
        )
        db.add(contrib)
        db.flush()
    contrib.xp_contributed += xp
    contrib.questions_answered += 1

    # Fix contributor count to be distinct users
    fscore.contributor_count = (
        db.query(func.count(models.FactionBattleContribution.id))
        .filter_by(battle_id=battle.id, faction_id=faction_id)
        .scalar() or 0
    )




def grant_safeguarded_reward(
    db: Session,
    user_id: int,
    session: models.QuizSession,
    selected_shuffled_index: int,
) -> dict:
    """
    Full safeguarded reward pipeline. Called by the quiz submit endpoint.

    Order:
      1. Validate answer (server-side)
      2. Check cooldown
      3. Check daily cap
      4. Grant reward + log audit
      5. Run pattern check (non-blocking but inline for simplicity)

    Returns a dict with the result details for the API response.

    On ANY internal error, fails SAFE (rejects reward, logs error).
    """
    now = datetime.now(timezone.utc)
    question = session.question
    question_id_str = str(question.id)

    try:
        
        is_correct = validate_server_answer(session, selected_shuffled_index)
        session.selected_option_index = selected_shuffled_index
        session.submitted_at = now
        session.is_correct = is_correct

        if not is_correct:
            _write_audit_log(
                db, user_id, question_id_str,
                coins=0, xp=0,
                reason_code=models.ReasonCode.invalid_answer,
                details="Wrong answer selected",
            )
            session.coins_awarded = 0
            session.xp_awarded = 0
            session.rejection_reason = "invalid_answer"
            db.commit()
            return {
                "is_correct": False,
                "coins_awarded": 0,
                "xp_awarded": 0,
                "rejection_reason": "invalid_answer",
                "detail": "Incorrect answer",
            }

 
        cooldown_detail = check_question_cooldown(session, now)
        if cooldown_detail:
            _write_audit_log(
                db, user_id, question_id_str,
                coins=0, xp=0,
                reason_code=models.ReasonCode.cooldown_violation,
                details=cooldown_detail,
            )
            session.coins_awarded = 0
            session.xp_awarded = 0
            session.rejection_reason = "cooldown_violation"
            db.commit()
            return {
                "is_correct": True,
                "coins_awarded": 0,
                "xp_awarded": 0,
                "rejection_reason": "cooldown_violation",
                "detail": cooldown_detail,
            }

        
        requested_coins = question.preview_coins
        requested_xp = question.preview_xp
        adj_coins, adj_xp, cap_detail = check_and_apply_daily_cap(
            db, user_id, requested_coins, requested_xp
        )

        if cap_detail and adj_coins == 0 and adj_xp == 0:
            _write_audit_log(
                db, user_id, question_id_str,
                coins=0, xp=0,
                reason_code=models.ReasonCode.cap_exceeded,
                details=cap_detail,
            )
            session.coins_awarded = 0
            session.xp_awarded = 0
            session.rejection_reason = "cap_exceeded"
            db.commit()
            return {
                "is_correct": True,
                "coins_awarded": 0,
                "xp_awarded": 0,
                "rejection_reason": "cap_exceeded",
                "detail": cap_detail,
            }

      
        wallet = earn_coins_and_xp(
            db, user_id,
            coins=adj_coins,
            xp=adj_xp,
            reason="quiz_correct",
        )

        _write_audit_log(
            db, user_id, question_id_str,
            coins=adj_coins, xp=adj_xp,
            reason_code=models.ReasonCode.granted,
            details=cap_detail, 
        )

        session.coins_awarded = adj_coins
        session.xp_awarded = adj_xp

      
        user = db.get(models.User, user_id)
        if user and user.faction_id:
            _update_battle_contribution(db, user_id, user.faction_id, adj_xp)

        db.commit()

      
        t_show = ensure_utc(session.question_shown_at)
        elapsed_ms = int((now - t_show).total_seconds() * 1000) if t_show else 0
        try:
            evaluate_suspicious_patterns(
                db, user_id, elapsed_ms, is_correct, question.id
            )
        except Exception as exc:
            logger.error("Pattern check error (non-fatal): %s", exc)

        return {
            "is_correct": True,
            "coins_awarded": adj_coins,
            "xp_awarded": adj_xp,
            "preview_coins": requested_coins,
            "preview_xp": requested_xp,
            "rejection_reason": None,
            "detail": cap_detail,
            "wallet_balance": wallet.balance,
            "wallet_xp": wallet.xp,
        }

    except Exception as exc:
       
        logger.error("Safeguard pipeline error for user %d: %s", user_id, exc)
        try:
            _write_audit_log(
                db, user_id, question_id_str,
                coins=0, xp=0,
                reason_code=models.ReasonCode.invalid_answer,
                details=f"Internal error (fail-safe): {exc}",
            )
            session.coins_awarded = 0
            session.xp_awarded = 0
            session.rejection_reason = "internal_error"
            db.commit()
        except Exception:
            db.rollback()

        return {
            "is_correct": False,
            "coins_awarded": 0,
            "xp_awarded": 0,
            "rejection_reason": "internal_error",
            "detail": "An internal error occurred. Reward rejected for safety.",
        }
