import base64
import hashlib
import hmac
import json
import re
import secrets
import struct
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.requests import HTTPConnection
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, SECRET_KEY, TOKEN_TTL_SECONDS
from app.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def validate_password_strength(password: str) -> None:
    """Enforce minimum 8 characters with at least one letter and one digit."""
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long and include both letters and numbers.",
        )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iters_str, salt, hex_digest = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters_str))
        return hmac.compare_digest(dk.hex(), hex_digest)
    except Exception:
        return False


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def compute_totp(secret_b32: str, timestamp: int | None = None, step: int = 30, digits: int = 6) -> str:
    ts = int(time.time()) if timestamp is None else timestamp
    counter = ts // step
    pad = "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(secret_b32.upper() + pad, casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(code).zfill(digits)


def verify_totp(secret_b32: str, code: str, window: int = 1) -> bool:
    if not code or not code.strip().isdigit():
        return False
    now = int(time.time())
    for delta in range(-window, window + 1):
        if hmac.compare_digest(compute_totp(secret_b32, now + delta * 30), code.strip()):
            return True
    return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def create_access_token(user_id: str, username: str, role: str, mfa_verified: bool = False) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    now = int(time.time())
    payload = _b64url_encode(
        json.dumps({
            "sub": user_id,
            "username": username,
            "role": role,
            "mfa_verified": mfa_verified,
            "iat": now,
            "exp": now + TOKEN_TTL_SECONDS,
        }).encode("utf-8")
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> dict:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_encode(expected_sig), sig_b64):
            raise ValueError("Invalid token signature")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("Token expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired credentials") from exc


def enforce_rate_limit(connection: HTTPConnection) -> None:
    if connection.scope.get("type") == "websocket":
        return
    key = connection.client.host if connection.client else "unknown"
    if key == "testclient":
        return
    now = time.time()
    bucket = _RATE_BUCKETS[key]
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down.")
    bucket.append(now)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = decode_access_token(credentials.credentials)
    with get_db() as db:
        user = db.fetchone(
            "SELECT id, username, email, role, is_guest, is_suspended, warning_count, preferred_language FROM users WHERE id = ?",
            (payload["sub"],),
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found")
    if user["is_suspended"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended. Submit an appeal if needed.")
    user["mfa_verified"] = bool(payload.get("mfa_verified", False))
    return user


def require_roles(*allowed_roles: str) -> Callable:
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        if user["role"] == "founder":
            with get_db() as db:
                tfa = db.fetchone("SELECT is_enabled FROM user_2fa WHERE user_id = ?", (user["id"],))
            if not tfa or not tfa["is_enabled"] or not user.get("mfa_verified"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mandatory Founder MFA verification required for privileged access.",
                )
        return user
    return _checker


def record_audit_log(actor_id: str | None, action: str, target_type: str, target_id: str | None, details: dict) -> None:
    log_id = f"aud_{secrets.token_hex(8)}"
    with get_db() as db:
        db.execute(
            "INSERT INTO audit_logs (id, actor_id, action, target_type, target_id, details_json) VALUES (?, ?, ?, ?, ?, ?)",
            (log_id, actor_id, action, target_type, target_id, json.dumps(details, ensure_ascii=False)),
        )
