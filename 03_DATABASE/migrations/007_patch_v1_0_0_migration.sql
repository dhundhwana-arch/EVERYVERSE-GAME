-- Migration v1.0.0: Founder/User TOTP 2FA & Secure Password Recovery (PostgreSQL & SQLite compatible)
CREATE TABLE IF NOT EXISTS user_2fa (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    totp_secret TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at BIGINT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
