import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/life", tags=["Family, Wellbeing & Multi-Dimensional Leaderboards"])


class FamilyMemberRequest(BaseModel):
    member_name: str = Field(..., min_length=2, max_length=40)
    relation_type: str = Field(..., pattern="^(parent|sibling|spouse|child|mentor|close_friend)$")


class WellbeingActivityRequest(BaseModel):
    activity: str = Field(..., pattern="^(rest|family_dinner|park_walk|festival|study_session)$")


@router.post("/family/add")
def add_family_member(req: FamilyMemberRequest, user: dict = Depends(get_current_user)):
    rel_id = f"fam_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute(
            "INSERT INTO family_relationships (id, user_id, member_name, relation_type, bond_score) VALUES (?, ?, ?, ?, 60)",
            (rel_id, user["id"], req.member_name, req.relation_type),
        )
    return {"relationship_id": rel_id, "member_name": req.member_name, "relation_type": req.relation_type, "bond_score": 60}


@router.get("/family")
def list_family(user: dict = Depends(get_current_user)):
    with get_db() as db:
        rows = db.fetchall("SELECT * FROM family_relationships WHERE user_id = ? ORDER BY bond_score DESC", (user["id"],))
    return {"family": rows}


@router.post("/wellbeing/activity")
def perform_wellbeing_activity(req: WellbeingActivityRequest, user: dict = Depends(get_current_user)):
    deltas = {
        "rest": (5, 30, -15),
        "family_dinner": (15, 10, -10),
        "park_walk": (10, -5, -12),
        "festival": (20, -10, -15),
        "study_session": (4, -15, 6),
    }
    dh, de, ds = deltas[req.activity]
    with get_db() as db:
        cur = db.fetchone("SELECT happiness, energy, stress FROM wellbeing_state WHERE user_id = ?", (user["id"],))
        h, e, s = (cur["happiness"], cur["energy"], cur["stress"]) if cur else (75, 100, 15)
        h = max(0, min(100, h + dh))
        e = max(0, min(100, e + de))
        s = max(0, min(100, s + ds))
        if cur:
            db.execute("UPDATE wellbeing_state SET happiness = ?, energy = ?, stress = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (h, e, s, user["id"]))
        else:
            db.execute("INSERT INTO wellbeing_state (user_id, happiness, energy, stress) VALUES (?, ?, ?, ?)", (user["id"], h, e, s))
        if req.activity == "family_dinner":
            db.execute("UPDATE family_relationships SET bond_score = MIN(100, bond_score + 5) WHERE user_id = ?", (user["id"],))
    return {"activity": req.activity, "happiness": h, "energy": e, "stress": s}


@router.get("/leaderboards")
def multi_dimensional_leaderboards():
    """Separate fair leaderboards (Knowledge, Public Trust, Financial) — Founder admin roles excluded from competitive rankings."""
    with get_db() as db:
        base_sql = """
            SELECT c.display_name, c.active_career_id, c.knowledge_points, c.reputation_score, c.virtual_money
            FROM characters c
            JOIN users u ON c.user_id = u.id
            WHERE u.role != 'founder' AND u.is_suspended = 0
        """
        by_knowledge = db.fetchall(base_sql + " ORDER BY c.knowledge_points DESC LIMIT 10")
        by_trust = db.fetchall(base_sql + " ORDER BY c.reputation_score DESC LIMIT 10")
        by_finance = db.fetchall(base_sql + " ORDER BY c.virtual_money DESC LIMIT 10")
    return {
        "policy": "Multi-dimensional success — wealth alone never defines player rank; Founder admin accounts excluded.",
        "knowledge_leaders": by_knowledge,
        "public_trust_leaders": by_trust,
        "financial_leaders": by_finance,
    }
