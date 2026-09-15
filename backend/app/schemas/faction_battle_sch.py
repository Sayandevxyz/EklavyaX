from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field




class FactionScoreResponse(BaseModel):
    """Score for a single faction in a battle."""
    faction_id: int
    faction_name: str
    color_hex: Optional[str] = None
    total_xp: int
    contributor_count: int


class ActiveBattleResponse(BaseModel):
    """Polling response for the currently active faction battle."""
    battle_id: int
    title: str
    status: str
    start_time: datetime
    end_time: datetime
    time_remaining_seconds: int
    scores: List[FactionScoreResponse]
    poll_interval_seconds: int


class NoBattleResponse(BaseModel):
    """Response when no battle is currently active."""
    status: str = "no_active_battle"
    message: str = "No faction war is currently active. Check back soon!"
    next_battle_start: Optional[datetime] = None




class ContributionEntry(BaseModel):
    """Individual contributor rank entry."""
    rank: int
    user_id: int
    username: str
    xp_contributed: int
    questions_answered: int


class BattleLeaderboardResponse(BaseModel):
    """Top contributors for a faction in a battle."""
    battle_id: int
    faction_id: int
    faction_name: str
    entries: List[ContributionEntry]



class BattleEndResponse(BaseModel):
    """Response after a battle is finalized."""
    battle_id: int
    status: str
    winning_faction_id: Optional[int] = None
    winning_faction_name: Optional[str] = None
    is_draw: bool
    scores: List[FactionScoreResponse]
    winner_bonus_coins: int
    winner_bonus_xp: int
    loser_participation_coins: int
    loser_participation_xp: int




class FactionChampion(BaseModel):
    user_id: int
    username: str
    xp: int
    level: int

class FactionDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    motto: str
    element: str
    domain: str
    color_hex: str
    icon: str
    score: int
    member_count: int
    active_battle_xp: int = 0
    top_champions: List[FactionChampion] = []



class BattleHistoryItem(BaseModel):
    battle_id: int
    title: str
    start_time: datetime
    end_time: datetime
    status: str
    winning_faction_id: Optional[int] = None
    winning_faction_name: Optional[str] = None
    total_xp_generated: int
    scores: List[FactionScoreResponse]

class BattleHistoryResponse(BaseModel):
    battles: List[BattleHistoryItem]

