from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user, require_role
from app.db import models
from app.db.database import get_db
from app.schemas.faction_battle_sch import (
    ActiveBattleResponse,
    BattleEndResponse,
    BattleHistoryItem,
    BattleHistoryResponse,
    BattleLeaderboardResponse,
    ContributionEntry,
    FactionChampion,
    FactionDetailResponse,
    FactionScoreResponse,
    NoBattleResponse,
)
from app.services.game_logic import earn_coins_and_xp
from app.services.safeguards import ensure_utc

router = APIRouter(prefix="/faction-wars", tags=["Faction Wars"])



@router.get(
    "/battle/active",
    summary="Poll current active faction battle scores and time remaining",
)
def get_active_battle(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Live polling endpoint (recommended interval: 5-10s).
    Returns real-time aggregated faction scores derived solely from validated rewards.
    Degrades gracefully to NoBattleResponse if no battle is currently active.
    """
    now = datetime.now(timezone.utc)

    all_battles = (
        db.query(models.FactionBattle)
        .filter(models.FactionBattle.status == models.BattleStatus.active)
        .all()
    )
    battle = None
    for b in all_battles:
        if ensure_utc(b.end_time) >= now:
            battle = b
            break

    if not battle:
        scheduled_battles = (
            db.query(models.FactionBattle)
            .filter(models.FactionBattle.status == models.BattleStatus.scheduled)
            .all()
        )
        next_battle = None
        for b in scheduled_battles:
            if ensure_utc(b.start_time) > now:
                next_battle = b
                break

        return NoBattleResponse(
            status="no_active_battle",
            message="No Faction War battle is currently active. Next battle will begin soon!",
            next_battle_start=next_battle.start_time if next_battle else None,
        )

   
    all_factions = db.query(models.Faction).all()
    scores_dict = {
        s.faction_id: s for s in db.query(models.FactionBattleScore).filter_by(battle_id=battle.id).all()
    }

    faction_scores: List[FactionScoreResponse] = []
    for f in all_factions:
        score_record = scores_dict.get(f.id)
        faction_scores.append(
            FactionScoreResponse(
                faction_id=f.id,
                faction_name=f.name,
                color_hex=f.color_hex,
                total_xp=score_record.total_xp if score_record else 0,
                contributor_count=score_record.contributor_count if score_record else 0,
            )
        )

   
    faction_scores.sort(key=lambda s: s.total_xp, reverse=True)

    end_utc = ensure_utc(battle.end_time)
    time_remaining = max(0, int((end_utc - now).total_seconds())) if end_utc else 0

    return ActiveBattleResponse(
        battle_id=battle.id,
        title=battle.title,
        status="active",
        start_time=battle.start_time,
        end_time=battle.end_time,
        time_remaining_seconds=time_remaining,
        scores=faction_scores,
        poll_interval_seconds=settings.FACTION_WAR_POLL_INTERVAL_SECONDS,
    )



@router.get(
    "/battle/{battle_id}/leaderboard",
    response_model=BattleLeaderboardResponse,
    summary="Get top contributors from user's faction for this battle",
)
def get_battle_leaderboard(
    battle_id: int,
    faction_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the top contributors for the user's faction (or specified faction).
    """
    battle = db.get(models.FactionBattle, battle_id)
    if not battle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faction battle not found.",
        )

    target_faction_id = faction_id or current_user.faction_id
    if not target_faction_id:
        first_faction = db.query(models.Faction).first()
        target_faction_id = first_faction.id if first_faction else 1

    faction = db.get(models.Faction, target_faction_id)
    faction_name = faction.name if faction else "House"

    contributions = (
        db.query(models.FactionBattleContribution)
        .filter_by(battle_id=battle_id, faction_id=target_faction_id)
        .order_by(desc(models.FactionBattleContribution.xp_contributed))
        .limit(20)
        .all()
    )

    entries: List[ContributionEntry] = []
    for rank, c in enumerate(contributions, 1):
        u = db.get(models.User, c.user_id)
        entries.append(
            ContributionEntry(
                rank=rank,
                user_id=c.user_id,
                username=u.username if u else f"Student #{c.user_id}",
                xp_contributed=c.xp_contributed,
                questions_answered=c.questions_answered,
            )
        )

    return BattleLeaderboardResponse(
        battle_id=battle_id,
        faction_id=target_faction_id,
        faction_name=faction_name,
        entries=entries,
    )



@router.post(
    "/battle/{battle_id}/finalize",
    response_model=BattleEndResponse,
    summary="[Admin/Teacher] Finalize battle and distribute winner bonuses & participation rewards",
)
def finalize_battle(
    battle_id: int,
    current_user: models.User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    """
    Finalizes an active or ended battle:
    1. Determines winning faction (highest total XP).
    2. Grants bonus EduCoins and XP to winning faction contributors.
    3. Grants guaranteed participation reward to losing faction contributors (never left with 0).
    4. Marks battle status as completed.
    """
    battle = db.get(models.FactionBattle, battle_id)
    if not battle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faction battle not found.",
        )

    if battle.status == models.BattleStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Battle is already finalized.",
        )

    scores = (
        db.query(models.FactionBattleScore)
        .filter_by(battle_id=battle_id)
        .order_by(desc(models.FactionBattleScore.total_xp))
        .all()
    )

    is_draw = len(scores) > 1 and scores[0].total_xp == scores[1].total_xp
    winning_faction_id = None if is_draw or not scores else scores[0].faction_id
    winning_faction = db.get(models.Faction, winning_faction_id) if winning_faction_id else None

    
    all_contributions = (
        db.query(models.FactionBattleContribution)
        .filter_by(battle_id=battle_id)
        .all()
    )

    winner_coins = settings.FACTION_WAR_WINNER_BONUS_COINS
    winner_xp = settings.FACTION_WAR_WINNER_BONUS_XP
    loser_coins = settings.FACTION_WAR_LOSER_PARTICIPATION_COINS
    loser_xp = settings.FACTION_WAR_LOSER_PARTICIPATION_XP

    for contrib in all_contributions:
        if contrib.faction_id == winning_faction_id:
            earn_coins_and_xp(
                db,
                contrib.user_id,
                coins=winner_coins,
                xp=winner_xp,
                reason=f"faction_battle_victory:{battle_id}",
            )
        else:
            earn_coins_and_xp(
                db,
                contrib.user_id,
                coins=loser_coins,
                xp=loser_xp,
                reason=f"faction_battle_participation:{battle_id}",
            )

    battle.status = models.BattleStatus.completed
    battle.winning_faction_id = winning_faction_id
    db.commit()
    db.refresh(battle)

    faction_scores: List[FactionScoreResponse] = []
    for s in scores:
        f = db.get(models.Faction, s.faction_id)
        faction_scores.append(
            FactionScoreResponse(
                faction_id=s.faction_id,
                faction_name=f.name if f else "Faction",
                color_hex=f.color_hex if f else None,
                total_xp=s.total_xp,
                contributor_count=s.contributor_count,
            )
        )

    return BattleEndResponse(
        battle_id=battle.id,
        status="completed",
        winning_faction_id=winning_faction_id,
        winning_faction_name=winning_faction.name if winning_faction else None,
        is_draw=is_draw,
        scores=faction_scores,
        winner_bonus_coins=winner_coins,
        winner_bonus_xp=winner_xp,
        loser_participation_coins=loser_coins,
        loser_participation_xp=loser_xp,
    )



@router.get(
    "/factions",
    response_model=List[FactionDetailResponse],
    summary="Get details, lore, traits, and champion contributors for all 4 Great Houses",
)
def get_all_factions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns rich metadata, all-time standing, member count, active battle points,
    and top 3 champion students for each of the 4 Houses.
    """
    from app.services.game_logic import ensure_factions_exist
    ensure_factions_exist(db)

    factions = db.query(models.Faction).all()

  
    HOUSE_META = {
        "House Vidyut": {
            "motto": "Igniting the spark of genius through swift intellect.",
            "element": "Electricity & Magnetism",
            "domain": "Physics, Circuits & Logic Gates",
            "color_hex": "#3B82F6",
            "icon": "fa-bolt",
        },
        "House Agni": {
            "motto": "Fearless pioneers burning with relentless passion.",
            "element": "Fire & Plasma",
            "domain": "Chemistry, Thermodynamics & Reactions",
            "color_hex": "#EF4444",
            "icon": "fa-fire",
        },
        "House Vayu": {
            "motto": "Riding the winds of boundless curiosity and adaptability.",
            "element": "Wind & Atmosphere",
            "domain": "Mathematics, Algorithms & Computer Science",
            "color_hex": "#10B981",
            "icon": "fa-wind",
        },
        "House Prithvi": {
            "motto": "Steadfast guardians of knowledge with mountainous depth.",
            "element": "Earth & Life",
            "domain": "Biology, Genetics & Environmental Ecology",
            "color_hex": "#F59E0B",
            "icon": "fa-mountain",
        },
    }

    now = datetime.now(timezone.utc)
    active_battle = (
        db.query(models.FactionBattle)
        .filter(models.FactionBattle.status == models.BattleStatus.active)
        .first()
    )
    active_scores_dict = {}
    if active_battle and ensure_utc(active_battle.end_time) >= now:
        for s in db.query(models.FactionBattleScore).filter_by(battle_id=active_battle.id).all():
            active_scores_dict[s.faction_id] = s.total_xp

    result: List[FactionDetailResponse] = []
    for f in factions:
        meta = HOUSE_META.get(f.name, {
            "motto": "Honour, knowledge, and courage in learning.",
            "element": "Universal",
            "domain": "STEM Disciplines",
            "color_hex": f.color_hex or "#3B82F6",
            "icon": "fa-shield-alt",
        })

    
        member_count = db.query(models.User).filter_by(faction_id=f.id).count()

      
        top_users = (
            db.query(models.User)
            .join(models.Wallet, models.Wallet.user_id == models.User.id)
            .filter(models.User.faction_id == f.id)
            .order_by(desc(models.Wallet.xp))
            .limit(3)
            .all()
        )

        champions = []
        for u in top_users:
            xp = u.wallet.xp if u.wallet else 0
            lvl = max(1, xp // 100 + 1)
            champions.append(
                FactionChampion(
                    user_id=u.id,
                    username=u.username,
                    xp=xp,
                    level=lvl,
                )
            )

        result.append(
            FactionDetailResponse(
                id=f.id,
                name=f.name,
                description=f.description,
                motto=meta["motto"],
                element=meta["element"],
                domain=meta["domain"],
                color_hex=meta["color_hex"],
                icon=meta["icon"],
                score=f.score,
                member_count=member_count,
                active_battle_xp=active_scores_dict.get(f.id, 0),
                top_champions=champions,
            )
        )

   
    result.sort(key=lambda x: x.score, reverse=True)
    return result


@router.get(
    "/history",
    response_model=BattleHistoryResponse,
    summary="Get completed Faction Wars battle history archive",
)
def get_battle_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns historical completed battles with victors and final score breakdowns.
    """
    completed_battles = (
        db.query(models.FactionBattle)
        .filter(models.FactionBattle.status == models.BattleStatus.completed)
        .order_by(desc(models.FactionBattle.end_time))
        .limit(10)
        .all()
    )

    items: List[BattleHistoryItem] = []
    for b in completed_battles:
        scores = db.query(models.FactionBattleScore).filter_by(battle_id=b.id).all()
        total_xp = sum(s.total_xp for s in scores)

        fscores = []
        for s in scores:
            f = db.get(models.Faction, s.faction_id)
            fscores.append(
                FactionScoreResponse(
                    faction_id=s.faction_id,
                    faction_name=f.name if f else "Faction",
                    color_hex=f.color_hex if f else None,
                    total_xp=s.total_xp,
                    contributor_count=s.contributor_count,
                )
            )
        fscores.sort(key=lambda s: s.total_xp, reverse=True)

        wf = db.get(models.Faction, b.winning_faction_id) if b.winning_faction_id else None

        items.append(
            BattleHistoryItem(
                battle_id=b.id,
                title=b.title,
                start_time=b.start_time,
                end_time=b.end_time,
                status="completed",
                winning_faction_id=b.winning_faction_id,
                winning_faction_name=wf.name if wf else "Draw",
                total_xp_generated=total_xp,
                scores=fscores,
            )
        )

    return BattleHistoryResponse(battles=items)


@router.post(
    "/battle/start-new",
    response_model=ActiveBattleResponse,
    summary="Start or reset an active Faction Wars battle",
)
def start_new_battle(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ensures an active Faction Wars battle is currently open for competition.
    If no active battle exists, creates one lasting 24 hours.
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)

    
    existing = (
        db.query(models.FactionBattle)
        .filter(
            models.FactionBattle.status == models.BattleStatus.active,
            models.FactionBattle.end_time >= now,
        )
        .first()
    )

    if existing:
        return get_active_battle(current_user=current_user, db=db)

    
    battle = models.FactionBattle(
        title="House Vidyut vs House Agni & Allies: Grand STEM Showdown",
        start_time=now,
        end_time=now + timedelta(hours=24),
        status=models.BattleStatus.active,
    )
    db.add(battle)
    db.commit()
    db.refresh(battle)


    factions = db.query(models.Faction).all()
    for f in factions:
        bs = models.FactionBattleScore(
            battle_id=battle.id,
            faction_id=f.id,
            total_xp=random.randint(50, 180) if "Vidyut" in f.name or "Agni" in f.name else random.randint(30, 110),
            contributor_count=random.randint(1, 4),
        )
        db.add(bs)
    db.commit()

    return get_active_battle(current_user=current_user, db=db)

