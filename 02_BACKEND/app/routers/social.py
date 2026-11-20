import json
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import decode_access_token, get_current_user, record_audit_log
from app.services.moderation_engine import evaluate_message

router = APIRouter(prefix="/social", tags=["Social World & Multiplayer"])

SOCIAL_LOCATIONS = [
    {"id": "central_plaza", "name": "Suryanagar Central Plaza", "type": "public_plaza"},
    {"id": "navabharat_univ", "name": "Navabharat Innovation University", "type": "university"},
    {"id": "skyline_cafe", "name": "Skyline Solar Cafe", "type": "cafe"},
    {"id": "unity_stadium", "name": "Unity Sports Stadium", "type": "stadium"},
]

ACTIVE_CONNECTIONS: dict[str, tuple[WebSocket, str]] = {}


class FriendActionRequest(BaseModel):
    target_user_id: str


class PartyCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    district: str = "Suryanagar Central Plaza"


class PartyJoinRequest(BaseModel):
    party_id: str


@router.get("/locations")
def get_social_locations():
    return {"locations": SOCIAL_LOCATIONS, "emotes": ["wave", "handshake", "celebrate", "dance", "sit_together", "group_photo"]}


@router.get("/presence")
def get_online_presence(user: dict = Depends(get_current_user)):
    return {"online_count": len(ACTIVE_CONNECTIONS), "online_usernames": [uname for _, uname in ACTIVE_CONNECTIONS.values()]}


@router.post("/friends/request")
def send_friend_request(req: FriendActionRequest, user: dict = Depends(get_current_user)):
    if req.target_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot add yourself")
    rel_id = f"fr_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute("INSERT INTO friendships (id, user_id, friend_user_id, status) VALUES (?, ?, ?, 'pending')", (rel_id, user["id"], req.target_user_id))
    return {"relationship_id": rel_id, "status": "pending"}


@router.post("/friends/accept")
def accept_friend_request(req: FriendActionRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        rel = db.fetchone(
            "SELECT id FROM friendships WHERE user_id = ? AND friend_user_id = ? AND status = 'pending'",
            (req.target_user_id, user["id"]),
        )
        if not rel:
            raise HTTPException(status_code=404, detail="Pending friend request not found")
        db.execute("UPDATE friendships SET status = 'accepted' WHERE id = ?", (rel["id"],))
    return {"relationship_id": rel["id"], "status": "accepted"}


@router.post("/party/create")
def create_party(req: PartyCreateRequest, user: dict = Depends(get_current_user)):
    party_id = f"pty_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute("INSERT INTO parties (id, name, leader_user_id, district) VALUES (?, ?, ?, ?)", (party_id, req.name, user["id"], req.district))
        db.execute("INSERT INTO party_members (party_id, user_id) VALUES (?, ?)", (party_id, user["id"]))
    return {"party_id": party_id, "name": req.name, "leader_user_id": user["id"]}


@router.post("/party/join")
def join_party(req: PartyJoinRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        party = db.fetchone("SELECT id FROM parties WHERE id = ?", (req.party_id,))
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        existing = db.fetchone("SELECT user_id FROM party_members WHERE party_id = ? AND user_id = ?", (req.party_id, user["id"]))
        if not existing:
            db.execute("INSERT INTO party_members (party_id, user_id) VALUES (?, ?)", (req.party_id, user["id"]))
    return {"party_id": req.party_id, "joined": True}


@router.get("/party/{party_id}")
def get_party(party_id: str, user: dict = Depends(get_current_user)):
    with get_db() as db:
        party = db.fetchone("SELECT * FROM parties WHERE id = ?", (party_id,))
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        members = db.fetchall("SELECT user_id, joined_at FROM party_members WHERE party_id = ?", (party_id,))
    return {"party": party, "members": members}


@router.post("/block")
def block_player(req: FriendActionRequest, user: dict = Depends(get_current_user)):
    rel_id = f"blk_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute("INSERT INTO friendships (id, user_id, friend_user_id, status, is_blocked) VALUES (?, ?, ?, 'blocked', 1)", (rel_id, user["id"], req.target_user_id))
    return {"blocked_user_id": req.target_user_id}


@router.post("/mute")
def mute_player(req: FriendActionRequest, user: dict = Depends(get_current_user)):
    rel_id = f"mut_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute("INSERT INTO friendships (id, user_id, friend_user_id, status, is_muted) VALUES (?, ?, ?, 'muted', 1)", (rel_id, user["id"], req.target_user_id))
    return {"muted_user_id": req.target_user_id}


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = ""):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = decode_access_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload["sub"]
    with get_db() as db:
        user = db.fetchone("SELECT id, username, is_suspended, chat_restricted_until, warning_count FROM users WHERE id = ?", (user_id,))
    if not user or user["is_suspended"] or user["chat_restricted_until"] > int(time.time()):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    ACTIVE_CONNECTIONS[user_id] = (websocket, user["username"])
    try:
        while True:
            raw_msg = await websocket.receive_text()
            mod = evaluate_message(raw_msg, channel="public_chat")
            if not mod["allowed"]:
                ev_id = f"mod_{secrets.token_hex(6)}"
                with get_db() as db:
                    new_stage = user["warning_count"] + 1
                    db.execute("UPDATE users SET warning_count = ? WHERE id = ?", (new_stage, user_id))
                    db.execute(
                        "INSERT INTO moderation_events (id, player_id, channel, message_excerpt, category, severity, decision, warning_stage, review_status) VALUES (?, ?, 'ws_chat', ?, ?, ?, ?, ?, ?)",
                        (ev_id, user_id, raw_msg[:180], mod["category"], mod["severity"], mod["decision"], new_stage, mod["review_status"]),
                    )
                    user["warning_count"] = new_stage
                record_audit_log(user_id, "ws_moderation_block", "moderation_event", ev_id, {"category": mod["category"]})
                await websocket.send_text(json.dumps({"delivered": False, "warning_stage": new_stage, "reason": mod["explanation"]}))
                continue

            outbound = json.dumps({"delivered": True, "sender": user["username"], "message": raw_msg})
            for conn, _ in list(ACTIVE_CONNECTIONS.values()):
                await conn.send_text(outbound)
    except WebSocketDisconnect:
        ACTIVE_CONNECTIONS.pop(user_id, None)
