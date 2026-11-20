# LIFEVERSE 2070 — Deployment & Termux-to-GitHub Guide

**CREATED BY DIVYESH BAMBHANIYA**

## 1. Push to GitHub from Termux (Android Tablet)
```bash
# Unzip the downloaded LIFEVERSE-2070.zip
unzip LIFEVERSE-2070.zip
cd LIFEVERSE-2070

# Run tests locally before pushing
PYTHONPATH=02_BACKEND python3 -m unittest discover -s 08_TESTS -v

# Initialize Git & Push to your private GitHub repo
git init
git add .
git commit -m "feat: initial working LIFEVERSE 2070 backend, moderation, db & Godot skeleton"
git branch -M main
git remote add origin https://github.com/dhundhwana-arch/LIFEVERSE-2070.git
git push -u origin main
```

## 2. Deploy Backend to Render + Neon PostgreSQL
1. Create a free **Neon** PostgreSQL database and copy the `postgresql://...` connection string.
2. In **Render**, click **New -> Blueprint** and connect your private `LIFEVERSE-2070` repository (uses `render.yaml`).
3. Set `DATABASE_URL` in Render Environment Variables to your Neon PostgreSQL URL.
4. Verify live healthcheck at `https://<your-render-url>/health`.
