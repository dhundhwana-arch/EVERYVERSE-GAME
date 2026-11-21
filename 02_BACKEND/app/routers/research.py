import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/research", tags=["Research Institutions & Space Tech (v0.6.0)"])


class StartResearchRequest(BaseModel):
    domain: str = Field(..., pattern="^(ai_safety|space_propulsion|semiconductors|climate_tech)$")
    title: str = Field(..., min_length=5, max_length=80)


class ContributeResearchRequest(BaseModel):
    project_id: str
    progress_increment: int = Field(50, ge=10, le=50)


@router.post("/projects/start")
def start_research_project(req: StartResearchRequest, user: dict = Depends(get_current_user)):
    proj_id = f"res_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute(
            "INSERT INTO research_projects (id, lead_user_id, domain, title, progress_pct, status) VALUES (?, ?, ?, ?, 0, 'active')",
            (proj_id, user["id"], req.domain, req.title),
        )
    return {"project_id": proj_id, "domain": req.domain, "title": req.title, "progress_pct": 0}


@router.post("/projects/contribute")
def contribute_research(req: ContributeResearchRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        proj = db.fetchone("SELECT * FROM research_projects WHERE id = ?", (req.project_id,))
        if not proj:
            raise HTTPException(status_code=404, detail="Research project not found")
        if proj["status"] == "published":
            raise HTTPException(status_code=409, detail="Research already peer-reviewed and published")
        new_pct = min(100, proj["progress_pct"] + req.progress_increment)
        new_status = "published" if new_pct >= 100 else "active"
        db.execute("UPDATE research_projects SET progress_pct = ?, status = ? WHERE id = ?", (new_pct, new_status, proj["id"]))
        if new_status == "published":
            db.execute("UPDATE characters SET knowledge_points = knowledge_points + 60, reputation_score = reputation_score + 30 WHERE user_id = ?", (user["id"],))
    return {"project_id": proj["id"], "progress_pct": new_pct, "status": new_status}
