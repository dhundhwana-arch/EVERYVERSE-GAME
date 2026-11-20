import json
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import FOUNDER_USERNAME
from app.database import get_db
from app.security import create_access_token, get_current_user, hash_password, record_audit_log, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: str | None = None
    password: str = Field(..., min_length=6)
    preferred_language: str = Field("en", pattern="^(en|gu|hi)$")


class LoginRequest(BaseModel):
    username: str
    password: str


class GuestUpgradeRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: str
    password: str = Field(..., min_length=6)


@router.post("/register")
def register(req: RegisterRequest):
    user_id = f"usr_{secrets.token_hex(8)}"
    role = "founder" if req.username.lower() == FOUNDER_USERNAME.lower() else "player"
    pw_hash = hash_password(req.password)
    with get_db() as db:
        existing = db.fetchone("SELECT id FROM users WHERE username = ?", (req.username,))
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")
        db.execute(
            "INSERT INTO users (id, username, email, password_hash, role, is_guest, preferred_language) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, req.username, req.email, pw_hash, role, 0, req.preferred_language),
        )
    record_audit_log(user_id, "account_registered", "user", user_id, {"role": role})
    token = create_access_token(user_id, req.username, role)
    return {"user_id": user_id, "username": req.username, "role": role, "access_token": token}


@router.post("/guest")
def create_guest(preferred_language: str = "en"):
    user_id = f"usr_{secrets.token_hex(8)}"
    username = f"guest_{secrets.token_hex(4)}"
    pw_hash = hash_password(secrets.token_hex(12))
    with get_db() as db:
        db.execute(
            "INSERT INTO users (id, username, email, password_hash, role, is_guest, preferred_language) VALUES (?, ?, NULL, ?, 'player', 1, ?)",
            (user_id, username, pw_hash, preferred_language),
        )
    token = create_access_token(user_id, username, "player")
    return {"user_id": user_id, "username": username, "is_guest": True, "access_token": token}


@router.post("/upgrade-guest")
def upgrade_guest(req: GuestUpgradeRequest, user: dict = Depends(get_current_user)):
    if not user["is_guest"]:
        raise HTTPException(status_code=400, detail="Account is already permanent")
    pw_hash = hash_password(req.password)
    with get_db() as db:
        if db.fetchone("SELECT id FROM users WHERE username = ? AND id != ?", (req.username, user["id"])):
            raise HTTPException(status_code=409, detail="Username already taken")
        db.execute(
            "UPDATE users SET username = ?, email = ?, password_hash = ?, is_guest = 0 WHERE id = ?",
            (req.username, req.email, pw_hash, user["id"]),
        )
    record_audit_log(user["id"], "guest_upgraded", "user", user["id"], {"username": req.username})
    token = create_access_token(user["id"], req.username, user["role"])
    return {"user_id": user["id"], "username": req.username, "is_guest": False, "access_token": token}


@router.post("/login")
def login(req: LoginRequest):
    with get_db() as db:
        row = db.fetchone(
            "SELECT id, username, password_hash, role, is_suspended, preferred_language FROM users WHERE username = ?",
            (req.username,),
        )
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if row["is_suspended"]:
        raise HTTPException(status_code=403, detail="Account suspended")
    token = create_access_token(row["id"], row["username"], row["role"])
    return {"user_id": row["id"], "username": row["username"], "role": row["role"], "preferred_language": row["preferred_language"], "access_token": token}


@router.get("/export-data")
def export_my_data(user: dict = Depends(get_current_user)):
    with get_db() as db:
        chars = db.fetchall("SELECT * FROM characters WHERE user_id = ?", (user["id"],))
        tasks = db.fetchall("SELECT * FROM career_tasks WHERE user_id = ?", (user["id"],))
        ledger = db.fetchall("SELECT * FROM economy_ledger WHERE user_id = ?", (user["id"],))
    return {"user": user, "characters": chars, "career_tasks": tasks, "economy_ledger": ledger}


@router.delete("/delete-account")
def delete_my_account(user: dict = Depends(get_current_user)):
    with get_db() as db:
        db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    record_audit_log(user["id"], "account_deleted", "user", user["id"], {})
    return {"deleted": True}
