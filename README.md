# LIFEVERSE 2070

**CREATED BY DIVYESH BAMBHANIYA**

An original, server-authoritative Open-World Life Simulation, Virtual Society, Career & Democratic Governance Platform with Multilingual Anti-Terrorism & Content Safety Moderation (Gujarati, Hindi, English).

## Architecture Overview
- **01_GAME/**: Godot 4 client skeleton (`project.godot`, `ApiClient.gd`, `GameManager.gd`, 3-language localization).
- **02_BACKEND/**: FastAPI server-authoritative backend (Auth/RBAC, Cloud Save & Restore, Dynamic Career & Task Engine, Fair PM Election Engine, Virtual Economy, Multilingual Moderation, Founder Dashboard API).
- **03_DATABASE/**: PostgreSQL production DDL + SQLite dual-engine local/Termux schema + backup/restore verification script.
- **04_WEBSITE/**: Official landing page & player portal.
- **05_ADMIN_PANEL/**: Private Founder Dashboard & Human Moderation Review UI.
- **06_SECURITY/**: Server-side private moderation configuration & Threat Model.
- **08_TESTS/**: Automated end-to-end test suite (`unittest` / `pytest` compatible).
- **09_DOCUMENTATION/**: Deployment guide (Termux -> GitHub -> Render + Neon PostgreSQL) & API reference.

## Quick Start (Termux / Local / Linux)
```bash
cd 02_BACKEND
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Automated Tests
```bash
PYTHONPATH=02_BACKEND python3 -m unittest discover -s 08_TESTS -v
```
