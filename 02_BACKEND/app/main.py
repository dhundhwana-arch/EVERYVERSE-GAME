from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import OFFICIAL_BRANDING
from app.database import init_db
from app.routers import admin, auth, careers, economy, moderation, players, social
from app.security import enforce_rate_limit


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LIFEVERSE 2070 Backend API",
    version="0.1.0",
    description=f"Server-Authoritative API for LIFEVERSE 2070 — {OFFICIAL_BRANDING}",
    lifespan=lifespan,
    dependencies=[Depends(enforce_rate_limit)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "project": "LIFEVERSE 2070", "branding": OFFICIAL_BRANDING}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(careers.router, prefix="/api/v1")
app.include_router(economy.router, prefix="/api/v1")
app.include_router(social.router, prefix="/api/v1")
app.include_router(moderation.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
