# LIFEVERSE 2070 — Patch v0.2.0 Manifest

**CREATED BY DIVYESH BAMBHANIYA**

## 1. Files Changed
### Added
- `01_GAME/scenes/MainMenu.tscn`
- `01_GAME/scenes/CharacterCreator.tscn`
- `01_GAME/scenes/SuryanagarPlaza.tscn`
- `01_GAME/scripts/MainMenu.gd`
- `01_GAME/scripts/CharacterCreator.gd`
- `01_GAME/scripts/PlayerController.gd`
- `03_DATABASE/migrations/003_patch_v0_2_0_migration.sql`
- `03_DATABASE/backup/backup_and_restore.py`
- `06_SECURITY/SECURITY_THREAT_MODEL.md`
- `08_TESTS/test_patch_v0_2_0.py`
- `09_DOCUMENTATION/API_DOCUMENTATION.md`
- `PATCH_MANIFEST.md`

### Modified
- `01_GAME/localization/messages.csv` (expanded Gujarati, Hindi, English keys)
- `02_BACKEND/requirements.txt` (added `websockets>=12.0`)
- `02_BACKEND/app/routers/careers.py` (fixed duplicate voting with DB + API `409` guard; implemented Stages 1–3 progression)
- `02_BACKEND/app/routers/social.py` (added `/friends/accept`, `/party/*`, `/presence`, and authenticated/moderated `/ws/chat`)
- `03_DATABASE/schemas/001_initial_postgresql.sql` (added `election_votes`, `parties`, `party_members`)
- `03_DATABASE/schemas/002_sqlite_compatible.sql` (added `election_votes`, `parties`, `party_members`)

### Deleted
- None.

## 2. Installation & Database Migration
```bash
# 1. Unzip patch over your existing LIFEVERSE-2070 directory
unzip -o LIFEVERSE-2070-Patch-v0.2.0.zip -d LIFEVERSE-2070/
cd LIFEVERSE-2070

# 2. Install updated dependencies
pip install -r 02_BACKEND/requirements.txt

# 3. Apply idempotent SQL migration (SQLite or PostgreSQL)
# SQLite example:
sqlite3 02_BACKEND/lifeverse_local.db < 03_DATABASE/migrations/003_patch_v0_2_0_migration.sql
# PostgreSQL (Neon/Render) example:
# psql "$DATABASE_URL" -f 03_DATABASE/migrations/003_patch_v0_2_0_migration.sql

# 4. Run full test suite
PYTHONPATH=02_BACKEND python3 -m unittest discover -s 08_TESTS -v
```

## 3. Rollback Instructions
```bash
# If using Git, revert modified files cleanly:
git checkout -- 01_GAME/localization/messages.csv 02_BACKEND/ 03_DATABASE/schemas/
# Database rollback (optional):
# DROP TABLE IF EXISTS party_members, parties, election_votes;
```
