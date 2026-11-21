"""
Secure Server-Side Founder Bootstrap Utility for LIFEVERSE 2070.
Founder privileges are NEVER granted via public /api/v1/auth/register.
Run this script via protected server shell / deployment job with environment variables:
  FOUNDER_BOOTSTRAP_USERNAME, FOUNDER_BOOTSTRAP_EMAIL, FOUNDER_BOOTSTRAP_PASSWORD, FOUNDER_TOTP_SECRET
"""
import os
import secrets

from app.database import get_db, init_db
from app.security import generate_totp_secret, hash_password, record_audit_log, validate_password_strength


def provision_founder(username: str, password: str, email: str | None = None, totp_secret: str | None = None) -> dict:
    validate_password_strength(password)
    secret = totp_secret or generate_totp_secret()
    pw_hash = hash_password(password)
    with get_db() as db:
        existing = db.fetchone("SELECT id FROM users WHERE username = ?", (username,))
        if existing:
            user_id = existing["id"]
            db.execute("UPDATE users SET role = 'founder', password_hash = ?, email = ? WHERE id = ?", (pw_hash, email, user_id))
        else:
            user_id = f"fnd_{secrets.token_hex(8)}"
            db.execute(
                "INSERT INTO users (id, username, email, password_hash, role, is_guest, preferred_language) VALUES (?, ?, ?, ?, 'founder', 0, 'en')",
                (user_id, username, email, pw_hash),
            )
        tfa = db.fetchone("SELECT user_id FROM user_2fa WHERE user_id = ?", (user_id,))
        if tfa:
            db.execute("UPDATE user_2fa SET totp_secret = ?, is_enabled = 1 WHERE user_id = ?", (secret, user_id))
        else:
            db.execute("INSERT INTO user_2fa (user_id, totp_secret, is_enabled) VALUES (?, ?, 1)", (user_id, secret))
    record_audit_log(user_id, "founder_provisioned_server_side", "user", user_id, {"mfa_enabled": True})
    return {"user_id": user_id, "username": username, "role": "founder", "totp_secret": secret}


if __name__ == "__main__":
    init_db()
    uname = os.environ["FOUNDER_BOOTSTRAP_USERNAME"]
    pwd = os.environ["FOUNDER_BOOTSTRAP_PASSWORD"]
    email = os.getenv("FOUNDER_BOOTSTRAP_EMAIL")
    totp = os.getenv("FOUNDER_TOTP_SECRET")
    res = provision_founder(uname, pwd, email=email, totp_secret=totp)
    print(f"Founder provisioned securely: {res['username']} (id={res['user_id']}, mfa_enabled=True)")
