from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import OFFICIAL_BRANDING
from app.database import init_db
from app.routers import (
    admin,
    auth,
    business,
    careers,
    economy,
    events,
    justice,
    life,
    marketplace,
    moderation,
    npcs,
    players,
    property as prop_router,
    research,
    social,
)
from app.security import enforce_rate_limit


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LIFEVERSE 2070 Backend API",
    version="1.0.0",
    description=f"Production Server-Authoritative API for LIFEVERSE 2070 — {OFFICIAL_BRANDING}",
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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0", "project": "LIFEVERSE 2070", "branding": OFFICIAL_BRANDING}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(careers.router, prefix="/api/v1")
app.include_router(economy.router, prefix="/api/v1")
app.include_router(life.router, prefix="/api/v1")
app.include_router(prop_router.router, prefix="/api/v1")
app.include_router(justice.router, prefix="/api/v1")
app.include_router(business.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1")
app.include_router(marketplace.router, prefix="/api/v1")
app.include_router(social.router, prefix="/api/v1")
app.include_router(npcs.router, prefix="/api/v1")
app.include_router(moderation.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
