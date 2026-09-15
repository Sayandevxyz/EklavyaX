from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import SessionLocal, get_db

router = APIRouter(tags=["Live Quiz Battles"])

# In-memory battle rooms manager for low-latency WebSocket communication
class BattleConnectionManager:
    def __init__(self):
        # room_code -> list of {"ws": WebSocket, "user_id": int, "username": str, "score": int}
        self.active_rooms: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self, room_code: str, websocket: WebSocket, user_id: int, username: str):
        await websocket.accept()
        if room_code not in self.active_rooms:
            self.active_rooms[room_code] = []
        self.active_rooms[room_code].append({
            "ws": websocket,
            "user_id": user_id,
            "username": username,
            "score": 0,
        })

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.active_rooms:
            self.active_rooms[room_code] = [
                p for p in self.active_rooms[room_code] if p["ws"] != websocket
            ]
            if not self.active_rooms[room_code]:
                del self.active_rooms[room_code]

    async def broadcast(self, room_code: str, message: Dict[str, Any]):
        if room_code in self.active_rooms:
            payload = json.dumps(message)
            for participant in self.active_rooms[room_code]:
                try:
                    await participant["ws"].send_text(payload)
                except Exception:
                    pass

    def get_participants(self, room_code: str) -> List[Dict[str, Any]]:
        if room_code not in self.active_rooms:
            return []
        return [
            {"user_id": p["user_id"], "username": p["username"], "score": p["score"]}
            for p in self.active_rooms[room_code]
        ]


manager = BattleConnectionManager()


class CreateRoomRequest(BaseModel):
    topic: str = "Physics & Mechanics"


@router.post("/api/live-quiz/rooms", summary="Create or find a live duel room")
def create_battle_room(
    payload: CreateRoomRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new live quiz battle duel room with 5 questions."""
    room_code = f"WAR-{secrets.token_hex(3).upper()}"

    # Fetch 5 sample questions
    questions = (
        db.query(models.QuizQuestion)
        .filter(models.QuizQuestion.topic.ilike(f"%{payload.topic[:4]}%"))
        .limit(5)
        .all()
    )
    if not questions:
        questions = db.query(models.QuizQuestion).limit(5).all()

    q_data = []
    for q in questions:
        q_data.append({
            "id": q.id,
            "prompt": q.prompt,
            "options": q.get_canonical_options(),
            "correct_index": q.correct_option_index,
        })

    room = models.LiveBattleRoom(
        room_code=room_code,
        host_id=current_user.id,
        topic=payload.topic,
        status="waiting",
        questions_json=json.dumps(q_data),
    )
    db.add(room)
    db.commit()

    return {
        "status": "created",
        "room_code": room_code,
        "topic": payload.topic,
        "question_count": len(q_data),
    }


@router.websocket("/ws/live-battle/{room_code}")
async def websocket_live_battle(
    websocket: WebSocket,
    room_code: str,
    username: str = "Warrior",
    user_id: int = 1,
):
    """
    WebSocket endpoint for real-time 1v1 live quiz duels.
    Handles player join, ready countdown, question answering, and live leaderboards.
    """
    room_code = room_code.upper()
    await manager.connect(room_code, websocket, user_id, username)

    # Broadcast updated participant list
    await manager.broadcast(
        room_code,
        {
            "type": "player_joined",
            "message": f"⚔️ {username} arena mein daakhil hue!",
            "participants": manager.get_participants(room_code),
        },
    )

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                event = json.loads(data_text)
            except Exception:
                continue

            event_type = event.get("type")

            if event_type == "start_game":
                # Fetch questions from database room
                db = SessionLocal()
                try:
                    db_room = db.query(models.LiveBattleRoom).filter_by(room_code=room_code).first()
                    questions = json.loads(db_room.questions_json) if db_room else []
                finally:
                    db.close()

                await manager.broadcast(
                    room_code,
                    {
                        "type": "game_started",
                        "questions": questions,
                        "time_per_question_sec": 15,
                    },
                )

            elif event_type == "submit_answer":
                # Increment score for participant
                points = event.get("points", 10)
                is_correct = event.get("is_correct", False)
                if is_correct and room_code in manager.active_rooms:
                    for p in manager.active_rooms[room_code]:
                        if p["user_id"] == user_id:
                            p["score"] += points

                await manager.broadcast(
                    room_code,
                    {
                        "type": "score_update",
                        "user_id": user_id,
                        "username": username,
                        "is_correct": is_correct,
                        "participants": manager.get_participants(room_code),
                    },
                )

            elif event_type == "finish_game":
                participants = manager.get_participants(room_code)
                winner = max(participants, key=lambda x: x["score"]) if participants else None
                await manager.broadcast(
                    room_code,
                    {
                        "type": "battle_ended",
                        "winner": winner,
                        "final_standings": sorted(participants, key=lambda x: x["score"], reverse=True),
                    },
                )

    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)
        await manager.broadcast(
            room_code,
            {
                "type": "player_left",
                "message": f"{username} disconnected.",
                "participants": manager.get_participants(room_code),
            },
        )
