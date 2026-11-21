import hashlib
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import FOUNDER_USERNAME
from app.database import get_db
from app.security import (
    create_access_token,
    generate_totp_secret,
    get_current_user,
    hash_password,
    record_audit_log,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["Authentication & 2FA"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: str | None = None
    password: str = Field(..., min_length=6)
    preferred_language: str = Field("en", pattern="^(en|gu|hi)$")


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


class GuestUpgradeRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: str
    password: str = Field(..., min_length=6)


class TotpVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetConfirmRequest(BaseModel):
    username: str
    reset_token: str
    new_password: str = Field(..., min_length=6)


@router.post("/register")
def register(req: RegisterRequest):
    user_id = f"usr_{secrets.token_hex(8)}"
    role = "founder" if req.username.lower() == FOUNDER_USERNAME.lower() else "player"
    pw_hash = hash_password(req.password)
    with get_db() as db:
        if db.fetchone("SELECT id FROM users WHERE username = ?", (req.username,)):
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


@router.post("/2fa/setup")
def setup_2fa(user: dict = Depends(get_current_user)):
    secret = generate_totp_secret()
    with get_db() as db:
        existing = db.fetchone("SELECT user_id FROM user_2fa WHERE user_id = ?", (user["id"],))
        if existing:
            db.execute("UPDATE user_2fa SET totp_secret = ?, is_enabled = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (secret, user["id"]))
        else:
            db.execute("INSERT INTO user_2fa (user_id, totp_secret, is_enabled) VALUES (?, ?, 0)", (user["id"], secret))
    uri = f"otpauth://totp/LIFEVERSE2070:{user['username']}?secret={secret}&issuer=LIFEVERSE2070"
    return {"totp_secret": secret, "otpauth_uri": uri, "enabled": False}


@router.post("/2fa/verify")
def verify_and_enable_2fa(req: TotpVerifyRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        row = db.fetchone("SELECT totp_secret FROM user_2fa WHERE user_id = ?", (user["id"],))
        if not row or not verify_totp(row["totp_secret"], req.code):
            raise HTTPException(status_code=400, detail="Invalid 2FA verification code")
        db.execute("UPDATE user_2fa SET is_enabled = 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user["id"],))
    record_audit_log(user["id"], "2fa_enabled", "user", user["id"], {})
    return {"enabled": True}


@router.post("/login")
def login(req: LoginRequest):
    with get_db() as db:
        row = db.fetchone(
            "SELECT id, username, password_hash, role, is_suspended, preferred_language FROM users WHERE username = ?",
            (req.username,),
        )
        tfa = db.fetchone("SELECT totp_secret, is_enabled FROM user_2fa WHERE user_id = ?", (row["id"],)) if row else None
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if row["is_suspended"]:
        raise HTTPException(status_code=403, detail="Account suspended")
    if tfa and tfa["is_enabled"]:
        if not req.totp_code or not verify_totp(tfa["totp_secret"], req.totp_code):
            raise HTTPException(status_code=401, detail="Valid 2FA TOTP code required")
    token = create_access_token(row["id"], row["username"], row["role"])
    return {"user_id": row["id"], "username": row["username"], "role": row["role"], "preferred_language": row["preferred_language"], "access_token": token}


@router.post("/password-reset/request")
def request_password_reset(req: PasswordResetRequest):
    raw_token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires = int(time.time()) + 900
    with get_db() as db:
        u = db.fetchone("SELECT id FROM users WHERE username = ?", (req.username,))
        if not u:
            raise HTTPException(status_code=404, detail="Account not found")
        db.execute(
            "INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, used) VALUES (?, ?, ?, ?, 0)",
            (f"rst_{secrets.token_hex(6)}", u["id"], token_hash, expires),
        )
    return {"reset_issued": True, "expires_in_seconds": 900, "dev_reset_token": raw_token}


@router.post("/password-reset/confirm")
def confirm_password_reset(req: PasswordResetConfirmRequest):
    token_hash = hashlib.sha256(req.reset_token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with get_db() as db:
        u = db.fetchone("SELECT id FROM users WHERE username = ?", (req.username,))
        if not u:
            raise HTTPException(status_code=404, detail="Account not found")
        rec = db.fetchone(
            "SELECT id, expires_at, used FROM password_reset_tokens WHERE user_id = ? AND token_hash = ? ORDER BY created_at DESC LIMIT 1",
            (u["id"], token_hash),
        )
        if not rec or rec["used"] or rec["expires_at"] < now:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(req.new_password), u["id"]))
        db.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (rec["id"],))
    record_audit_log(u["id"], "password_reset_completed", "user", u["id"], {})
    return {"password_updated": True}


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
