# LIFEVERSE 2070 — Patch v0.3.0 Manifest

**CREATED BY DIVYESH BAMBHANIYA**

## 1. Files Changed
### Added
- `01_GAME/scripts/NpcInteractable.gd`
- `01_GAME/scripts/DialogueUI.gd`
- `02_BACKEND/app/routers/npcs.py`
- `03_DATABASE/migrations/004_patch_v0_3_0_migration.sql`
- `08_TESTS/test_patch_v0_3_0.py`
- `PATCH_MANIFEST_v0.3.0.md`

### Modified
- `01_GAME/scenes/SuryanagarPlaza.tscn` (added Navabharat Innovation University Dome, Skyline Solar Cafe, Civic Fountain, 3 interactable NPCs, and Dialogue HUD)
- `01_GAME/localization/messages.csv` (added NPC dialogue & button keys in English, Gujarati, Hindi)
- `02_BACKEND/app/main.py` (registered `/api/v1/npcs` router and updated API version to `0.3.0`)
- `03_DATABASE/schemas/001_initial_postgresql.sql` (added `npc_interactions` table)
- `03_DATABASE/schemas/002_sqlite_compatible.sql` (added `npc_interactions` table)
- `04_WEBSITE/index.html` (upgraded to interactive Suryanagar Player Portal with Auth, Avatar, NPC Talk, Career, and Moderation Tester)
- `05_ADMIN_PANEL/founder_dashboard.html` (upgraded with Founder login, live overview/moderation queue, and Appeal Review controls)

### Deleted
- None.

## 2. Installation & Migration (Termux -> GitHub)
```bash
# Unzip patch over ~/projects/LIFEVERSE-2070
unzip -o /sdcard/Download/LIFEVERSE-2070-Patch-v0.3.0.zip -d ~/projects/LIFEVERSE-2070/
cd ~/projects/LIFEVERSE-2070

# Run all 13 automated tests
PYTHONPATH=02_BACKEND python3 -m unittest discover -s 08_TESTS -v

# Commit & push to EVERYVERSE-GAME
git add .
git commit -m "feat: LIFEVERSE 2070 v0.3.0 3D landmarks, NPC dialogue engine & interactive dashboards"
git push origin main
```

## 3. Rollback
```bash
git checkout -- 01_GAME/ 02_BACKEND/app/main.py 03_DATABASE/schemas/ 04_WEBSITE/ 05_ADMIN_PANEL/
```
