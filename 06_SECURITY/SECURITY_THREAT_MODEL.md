# LIFEVERSE 2070 — Security Threat Model

**CREATED BY DIVYESH BAMBHANIYA**

| Threat | Mitigation Implemented | Residual Risk / Honest Limitation |
| --- | --- | --- |
| **Client-side currency tampering** | Server-authoritative `economy_ledger` & `characters.virtual_money`; `client_claimed_balance` ignored. | None for server-synced currency; local UI display can still be visually spoofed on rooted devices. |
| **Duplicate election voting** | `UNIQUE(election_id, voter_user_id)` constraint in `election_votes` + `409 Conflict` API check. | Multi-account Sybil voting requires email/phone verification or CAPTCHA before public scale. |
| **Privilege escalation to Founder** | Role assigned server-side; `require_roles("founder")` checks JWT + DB user row; passwords never returned. | `SECRET_KEY` must be rotated via env vars outside GitHub. |
| **Multilingual moderation evasion** | `normalize_text()` strips homoglyphs, leetspeak, split letters, and repeated chars across Gujarati, Hindi, English, and Romanized variants. | Novel slang/image-embedded text requires OCR/LLM upgrades in later phases. |
| **Unauthenticated WebSocket spam** | `/api/v1/social/ws/chat` validates JWT, `is_suspended`, and `chat_restricted_until` before `accept()`, and runs `evaluate_message()` on every frame. | Production deployment should add per-connection message rate limiting. |
| **Backup corruption** | `backup_and_restore.py` generates and verifies SHA-256 checksum manifests before restore. | Off-site encrypted cloud replication (S3/R2) must be configured in production. |
