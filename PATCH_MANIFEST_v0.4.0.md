# LIFEVERSE 2070 — Patch v0.4.0 Manifest

**CREATED BY DIVYESH BAMBHANIYA**

## 1. Files Changed
### Added
- `01_GAME/scenes/CareerPortal.tscn`
- `01_GAME/scenes/PlayerHUD.tscn`
- `01_GAME/scripts/CareerPortal.gd`
- `01_GAME/scripts/PlayerHUD.gd`
- `02_BACKEND/app/data/career_registry.json` (30 functional careers across 14 categories)
- `02_BACKEND/app/routers/life.py` (Family, Wellbeing, Multi-Dimensional Leaderboards)
- `02_BACKEND/app/routers/property.py` (Server-authoritative Housing & Vehicles)
- `03_DATABASE/migrations/005_patch_v0_4_0_migration.sql`
- `08_TESTS/test_patch_v0_4_0.py`
- `PATCH_MANIFEST_v0.4.0.md`

### Modified
- `01_GAME/localization/messages.csv` (added Career Portal & HUD keys in EN/GU/HI)
- `02_BACKEND/app/routers/careers.py` (loads 30-career JSON registry with category filter)
- `02_BACKEND/app/main.py` (registered `/api/v1/life` and `/api/v1/property`, version `0.4.0`)
- `03_DATABASE/schemas/001_initial_postgresql.sql` (added family, wellbeing, properties, vehicles tables)
- `03_DATABASE/schemas/002_sqlite_compatible.sql` (added family, wellbeing, properties, vehicles tables)

### Deleted
- None.

## 2. Installation & Push (Termux -> GitHub)
```bash
cd ~/projects/LIFEVERSE-2070
cp -r /sdcard/LIFEVERSE-2070-Patch-v0.4.0/* .

# Run all 16 automated tests
PYTHONPATH=02_BACKEND python3 -m unittest discover -s 08_TESTS -v

git add .
git commit -m "feat: LIFEVERSE 2070 v0.4.0 30-career registry, family, property/vehicles & leaderboards"
git push origin main
```
