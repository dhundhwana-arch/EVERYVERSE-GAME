# LIFEVERSE 2070 — API Documentation (v0.2.0)

**CREATED BY DIVYESH BAMBHANIYA**

Base URL: `/api/v1` (Healthcheck: `GET /health`)

## Authentication (`/auth`)
- `POST /auth/register` — Register player (or Founder if username matches `FOUNDER_USERNAME`).
- `POST /auth/guest` — Create temporary guest session.
- `POST /auth/upgrade-guest` — Upgrade guest to permanent account.
- `POST /auth/login` — Authenticate and receive Bearer JWT.
- `GET /auth/export-data` — Export user's saved JSON data.
- `DELETE /auth/delete-account` — Permanently delete user account.

## Players & Cloud Save (`/players`)
- `POST /players/character` — Create character (`manual`, `photo_reference` requiring `photo_consent_granted=true`, or `ai_concept`).
- `GET /players/save` — Load latest cloud save.
- `PUT /players/save` — Sync world position, inventory, and language.

## Careers & Elections (`/careers`)
- `GET /careers/registry` — List starter careers and onboarding choices.
- `POST /careers/select` — Select career and receive Stage 1 task.
- `POST /careers/submit-task` — Submit task score (`>= 60` advances Stages 1→2→3; `< 60` offers zero-loss retry).
- `POST /careers/elections/create`, `POST /careers/elections/register-candidate`
- `POST /careers/elections/{election_id}/vote/{candidate_id}` — Cast vote (strictly 1 vote per player per election; returns `409` on duplicate).
- `POST /careers/elections/{election_id}/finalize` — Appoint PM + Cabinet fallback roles.

## Social & WebSocket (`/social`)
- `GET /social/locations`, `GET /social/presence`
- `POST /social/friends/request`, `POST /social/friends/accept`
- `POST /social/party/create`, `POST /social/party/join`, `GET /social/party/{party_id}`
- `POST /social/block`, `POST /social/mute`
- `WS /social/ws/chat?token=<JWT>` — Authenticated, moderated real-time chat.

## Moderation (`/moderation`) & Founder (`/admin`)
- `POST /moderation/check-message`, `POST /moderation/report`, `POST /moderation/appeal`
- `GET /moderation/dashboard`, `POST /moderation/review-appeal` *(Moderator/Founder only)*
- `GET /admin/overview` *(Founder only)*
