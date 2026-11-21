import hashlib
import secrets
import smtplib
import time
from email.message import EmailMessage
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from app.database import get_db
from app.security import (
    create_access_token,
    generate_totp_secret,
    get_current_user,
    hash_password,
    record_audit_log,
    validate_password_strength,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["Authentication & 2FA"])

# Optional server-side email delivery hook (for tests); NEVER returned in API responses
_EMAIL_DELIVERY_HOOK: Callable[[str, str], None] | None = None


def _deliver_reset_email(recipient_email: str, raw_token: str) -> None:
    if _EMAIL_DELIVERY_HOOK is not None:
        _EMAIL_DELIVERY_HOOK(recipient_email, raw_token)
        return
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM):
        raise HTTPException(
            status_code=503,
            detail="Password reset email delivery is not configured. Contact support.",
        )
    msg = EmailMessage()
    msg["Subject"] = "LIFEVERSE 2070 — Password Reset Token"
    msg["From"] = SMTP_FROM
    msg["To"] = recipient_email
    msg.set_content(f"Use this single-use token within 15 minutes to reset your LIFEVERSE 2070 password:\n\n{raw_token}")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: str | None = None
    password: str = Field(..., min_length=8)
    preferred_language: str = Field("en", pattern="^(en|gu|hi)$")


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


class GuestUpgradeRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: str
    password: str = Field(..., min_length=8)


class TotpSetupRequest(BaseModel):
    current_totp_code: str | None = None


class TotpVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetConfirmRequest(BaseModel):
    username: str
    reset_token: str
    new_password: str = Field(..., min_length=8)


@router.post("/register")
def register(req: RegisterRequest):
    validate_password_strength(req.password)
    user_id = f"usr_{secrets.token_hex(8)}"
    # SECURITY FIX: Public registration ALWAYS assigns 'player'. Founder role is server-side pre-provisioned only.
    role = "player"
    pw_hash = hash_password(req.password)
    with get_db() as db:
        if db.fetchone("SELECT id FROM users WHERE username = ?", (req.username,)):
            raise HTTPException(status_code=409, detail="Username already exists")
        db.execute(
            "INSERT INTO users (id, username, email, password_hash, role, is_guest, preferred_language) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, req.username, req.email, pw_hash, role, 0, req.preferred_language),
        )
    record_audit_log(user_id, "account_registered", "user", user_id, {"role": role})
    token = create_access_token(user_id, req.username, role, mfa_verified=False)
    return {"user_id": user_id, "username": req.username, "role": role, "access_token": token}


@router.post("/guest")
def create_guest(preferred_language: str = "en"):
    user_id = f"usr_{secrets.token_hex(8)}"
    username = f"guest_{secrets.token_hex(4)}"
    pw_hash = hash_password(secrets.token_hex(12) + "A1")
    with get_db() as db:
        db.execute(
            "INSERT INTO users (id, username, email, password_hash, role, is_guest, preferred_language) VALUES (?, ?, NULL, ?, 'player', 1, ?)",
            (user_id, username, pw_hash, preferred_language),
        )
    token = create_access_token(user_id, username, "player", mfa_verified=False)
    return {"user_id": user_id, "username": username, "is_guest": True, "access_token": token}


@router.post("/upgrade-guest")
def upgrade_guest(req: GuestUpgradeRequest, user: dict = Depends(get_current_user)):
    if not user["is_guest"]:
        raise HTTPException(status_code=400, detail="Account is already permanent")
    validate_password_strength(req.password)
    pw_hash = hash_password(req.password)
    with get_db() as db:
        if db.fetchone("SELECT id FROM users WHERE username = ? AND id != ?", (req.username, user["id"])):
            raise HTTPException(status_code=409, detail="Username already taken")
        db.execute(
            "UPDATE users SET username = ?, email = ?, password_hash = ?, is_guest = 0 WHERE id = ?",
            (req.username, req.email, pw_hash, user["id"]),
        )
    record_audit_log(user["id"], "guest_upgraded", "user", user["id"], {"username": req.username})
    token = create_access_token(user["id"], req.username, user["role"], mfa_verified=user.get("mfa_verified", False))
    return {"user_id": user["id"], "username": req.username, "is_guest": False, "access_token": token}


@router.post("/2fa/setup")
def setup_2fa(req: TotpSetupRequest | None = None, user: dict = Depends(get_current_user)):
    with get_db() as db:
        existing = db.fetchone("SELECT totp_secret, is_enabled FROM user_2fa WHERE user_id = ?", (user["id"],))
        # SECURITY FIX: Prevent overwriting enabled 2FA without verifying current TOTP code
        if existing and existing["is_enabled"]:
            current_code = req.current_totp_code if req else None
            if not current_code or not verify_totp(existing["totp_secret"], current_code):
                raise HTTPException(status_code=403, detail="Current valid 2FA code required to rotate an enabled 2FA secret.")
        secret = generate_totp_secret()
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

    mfa_verified = False
    # SECURITY FIX: Mandatory MFA for Founder accounts — cannot log in without enabled TOTP + valid code
    if row["role"] == "founder":
        if not tfa or not tfa["is_enabled"]:
            raise HTTPException(status_code=403, detail="Founder account requires server-provisioned MFA before login.")
        if not req.totp_code or not verify_totp(tfa["totp_secret"], req.totp_code):
            raise HTTPException(status_code=401, detail="Valid Founder 2FA TOTP code required.")
        mfa_verified = True
    elif tfa and tfa["is_enabled"]:
        if not req.totp_code or not verify_totp(tfa["totp_secret"], req.totp_code):
            raise HTTPException(status_code=401, detail="Valid 2FA TOTP code required")
        mfa_verified = True

    token = create_access_token(row["id"], row["username"], row["role"], mfa_verified=mfa_verified)
    return {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "mfa_verified": mfa_verified,
        "preferred_language": row["preferred_language"],
        "access_token": token,
    }


@router.post("/password-reset/request")
def request_password_reset(req: PasswordResetRequest):
    with get_db() as db:
        u = db.fetchone("SELECT id, email, role FROM users WHERE username = ?", (req.username,))
        if not u:
            raise HTTPException(status_code=404, detail="Account not found")
        if u["role"] == "founder":
            raise HTTPException(status_code=403, detail="Founder password reset must be performed via server-side recovery procedure.")
        if not u["email"]:
            raise HTTPException(status_code=400, detail="No verified email address on file for password reset.")

        raw_token = secrets.token_urlsafe(24)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires = int(time.time()) + 900

        # Deliver via configured email provider BEFORE persisting/returning; fails safely with 503 if unconfigured
        _deliver_reset_email(u["email"], raw_token)
        db.execute(
            "INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, used) VALUES (?, ?, ?, ?, 0)",
            (f"rst_{secrets.token_hex(6)}", u["id"], token_hash, expires),
        )
    # SECURITY FIX: Never expose dev_reset_token in API response
    return {"reset_issued": True, "expires_in_seconds": 900, "message": "If email delivery succeeded, check your inbox for the reset token."}


@router.post("/password-reset/confirm")
def confirm_password_reset(req: PasswordResetConfirmRequest):
    validate_password_strength(req.new_password)
    token_hash = hashlib.sha256(req.reset_token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with get_db() as db:
        u = db.fetchone("SELECT id, role FROM users WHERE username = ?", (req.username,))
        if not u or u["role"] == "founder":
            raise HTTPException(status_code=403, detail="Password reset not permitted for this account.")
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
    if user["role"] == "founder":
        raise HTTPException(status_code=403, detail="Founder account cannot be deleted via self-service endpoint.")
    with get_db() as db:
        db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    record_audit_log(user["id"], "account_deleted", "user", user["id"], {})
    return {"deleted": True}
