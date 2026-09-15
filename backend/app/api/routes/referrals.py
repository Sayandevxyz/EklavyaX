from __future__ import annotations

import secrets
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/referrals", tags=["Referral System"])


class ApplyReferralRequest(BaseModel):
    referral_code: str


@router.get("/my-code", summary="Get or create user's unique referral code")
def get_my_referral_code(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve user's referral code and shareable invite link."""
    # Find any existing referral record created by this user
    existing = db.query(models.Referral).filter_by(referrer_id=current_user.id).first()
    if not existing:
        code = f"EKL-{current_user.username.upper()[:4]}-{secrets.token_hex(2).upper()}"
        ref = models.Referral(
            referrer_id=current_user.id,
            referral_code=code,
            bonus_coins=settings.REFERRAL_BONUS_COINS,
            bonus_xp=settings.REFERRAL_BONUS_XP,
        )
        db.add(ref)
        db.commit()
        referral_code = code
    else:
        referral_code = existing.referral_code

    # Count successfully completed referrals
    successful_referrals = (
        db.query(models.Referral)
        .filter(models.Referral.referrer_id == current_user.id, models.Referral.referee_id != None)
        .count()
    )

    total_coins_earned = successful_referrals * settings.REFERRAL_BONUS_COINS
    total_xp_earned = successful_referrals * settings.REFERRAL_BONUS_XP

    return {
        "referral_code": referral_code,
        "invite_link": f"/student/student_login.html?ref={referral_code}",
        "reward_per_invite": {
            "coins": settings.REFERRAL_BONUS_COINS,
            "xp": settings.REFERRAL_BONUS_XP,
        },
        "successful_referrals_count": successful_referrals,
        "total_coins_earned": total_coins_earned,
        "total_xp_earned": total_xp_earned,
    }


@router.post("/apply", summary="Apply a friend's referral code")
def apply_referral_code(
    payload: ApplyReferralRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Claim referral bonus by applying an invite code."""
    code = payload.referral_code.strip().upper()

    # Check if user already used a referral code
    already_used = (
        db.query(models.Referral)
        .filter_by(referee_id=current_user.id)
        .first()
    )
    if already_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aap pehle hi ek referral code use kar chuke hain.",
        )

    # Find referrer
    ref_record = (
        db.query(models.Referral)
        .filter(models.Referral.referral_code == code)
        .first()
    )
    if not ref_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral code galat hai ya exist nahi karta.",
        )

    if ref_record.referrer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aap apna khud ka referral code use nahi kar sakte.",
        )

    # Create referral link record
    claimed_ref = models.Referral(
        referrer_id=ref_record.referrer_id,
        referee_id=current_user.id,
        referral_code=code,
        bonus_coins=settings.REFERRAL_BONUS_COINS,
        bonus_xp=settings.REFERRAL_BONUS_XP,
        is_claimed=True,
    )
    db.add(claimed_ref)

    # Award coins & XP to referee (current user)
    if current_user.wallet:
        current_user.wallet.balance += settings.REFERRAL_BONUS_COINS
        current_user.wallet.xp += settings.REFERRAL_BONUS_XP

    # Award coins & XP to referrer
    referrer = db.query(models.User).filter_by(id=ref_record.referrer_id).first()
    if referrer and referrer.wallet:
        referrer.wallet.balance += settings.REFERRAL_BONUS_COINS
        referrer.wallet.xp += settings.REFERRAL_BONUS_XP

        notif = models.Notification(
            user_id=referrer.id,
            title="🎉 Referral Bonus Received!",
            message=f"{current_user.username} ne aapka referral code use kiya! Aapko +{settings.REFERRAL_BONUS_COINS} EduCoins aur +{settings.REFERRAL_BONUS_XP} XP mile hain!",
            notif_type="referral_bonus",
            action_url="../student/student_dashboard.html",
        )
        db.add(notif)

    db.commit()

    return {
        "status": "applied",
        "bonus_coins": settings.REFERRAL_BONUS_COINS,
        "bonus_xp": settings.REFERRAL_BONUS_XP,
        "message": f"Referral code safaltapoorvak apply hua! +{settings.REFERRAL_BONUS_COINS} EduCoins aapke wallet mein add ho gaye.",
    }
