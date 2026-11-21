# LIFEVERSE 2070 — Combined Patch v0.5.0 + v0.6.0 Manifest

**CREATED BY DIVYESH BAMBHANIYA**

## 1. Files Changed
### Added
- `.github/workflows/ci.yml` (GitHub Actions automated CI running all `unittest` suites on every push)
- `01_GAME/scenes/BusinessAndEventsUI.tscn`
- `01_GAME/scenes/ResearchLab.tscn`
- `01_GAME/scripts/BusinessAndEventsUI.gd`
- `01_GAME/scripts/ResearchLab.gd`
- `02_BACKEND/app/routers/justice.py` (v0.5.0: Law, Police & Judiciary cases/verdicts)
- `02_BACKEND/app/routers/business.py` (v0.5.0: Startups & realistic profit/loss virtual cycles)
- `02_BACKEND/app/routers/events.py` (v0.5.0: Festivals, Trivia Mini-Games & Social Achievements)
- `02_BACKEND/app/routers/research.py` (v0.6.0: Research Institutions & Space/Semiconductor Labs)
- `02_BACKEND/app/routers/marketplace.py` (v0.6.0: Player-to-Player Virtual Services & Crafted Items Marketplace)
- `03_DATABASE/migrations/006_patch_v0_6_0_migration.sql`
- `08_TESTS/test_patch_v0_5_and_v0_6.py`
- `PATCH_MANIFEST_v0.6.0.md`

### Modified
- `01_GAME/localization/messages.csv` (added Business, Festivals & Research keys in EN/GU/HI)
- `02_BACKEND/app/main.py` (mounted all 5 new routers, version `0.6.0`)
- `03_DATABASE/schemas/001_initial_postgresql.sql`
- `03_DATABASE/schemas/002_sqlite_compatible.sql`

### Deleted
- None.

## 2. Installation & Push (Termux -> GitHub)
```bash
cd ~/projects/LIFEVERSE-2070
cp -r /sdcard/LIFEVERSE-2070-Patch-v0.6.0/* .

# Verify all 20 automated tests pass
PYTHONPATH=02_BACKEND python3 -m unittest discover -s 08_TESTS -v

git add .
git commit -m "feat: LIFEVERSE 2070 v0.5.0 + v0.6.0 justice, business, festivals, research, marketplace & CI"
git push origin main
```
