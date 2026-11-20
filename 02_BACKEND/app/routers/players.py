import json
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/players", tags=["Players & Cloud Save"])


class CharacterCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=40)
    avatar_method: str = Field("manual", pattern="^(manual|photo_reference|ai_concept)$")
    avatar_config: dict = Field(default_factory=dict)
    photo_consent_granted: bool = False
    privacy_level: str = Field("public", pattern="^(public|friends_only|private)$")


class CloudSaveRequest(BaseModel):
    world_position: dict
    inventory: list | None = None
    preferred_language: str | None = Field(None, pattern="^(en|gu|hi)$")


@router.post("/character")
def create_character(req: CharacterCreateRequest, user: dict = Depends(get_current_user)):
    if req.avatar_method == "photo_reference" and not req.photo_consent_granted:
        raise HTTPException(status_code=400, detail="Explicit permission is required before photo-based avatar processing.")
    char_id = f"chr_{secrets.token_hex(8)}"
    with get_db() as db:
        db.execute(
            """INSERT INTO characters (id, user_id, display_name, avatar_method, avatar_config_json, photo_consent_granted, privacy_level)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                char_id,
                user["id"],
                req.display_name,
                req.avatar_method,
                json.dumps(req.avatar_config, ensure_ascii=False),
                1 if req.photo_consent_granted else 0,
                req.privacy_level,
            ),
        )
    return {"character_id": char_id, "display_name": req.display_name, "avatar_method": req.avatar_method}


@router.get("/save")
def load_cloud_save(user: dict = Depends(get_current_user)):
    with get_db() as db:
        char = db.fetchone("SELECT * FROM characters WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (user["id"],))
    if not char:
        raise HTTPException(status_code=404, detail="No character save found")
    return {
        "character_id": char["id"],
        "display_name": char["display_name"],
        "country_name": char["country_name"],
        "city_name": char["city_name"],
        "avatar_method": char["avatar_method"],
        "avatar_config": json.loads(char["avatar_config_json"]),
        "privacy_level": char["privacy_level"],
        "virtual_money": char["virtual_money"],
        "knowledge_points": char["knowledge_points"],
        "reputation_score": char["reputation_score"],
        "life_level": char["life_level"],
        "active_career_id": char["active_career_id"],
        "skills": json.loads(char["skills_json"]),
        "achievements": json.loads(char["achievements_json"]),
        "inventory": json.loads(char["inventory_json"]),
        "world_position": json.loads(char["world_position_json"]),
        "save_version": char["save_version"],
    }


@router.put("/save")
def sync_cloud_save(req: CloudSaveRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        char = db.fetchone("SELECT id, save_version, inventory_json FROM characters WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (user["id"],))
        if not char:
            raise HTTPException(status_code=404, detail="Create a character first")
        inv_json = json.dumps(req.inventory, ensure_ascii=False) if req.inventory is not None else char["inventory_json"]
        new_ver = char["save_version"] + 1
        db.execute(
            "UPDATE characters SET world_position_json = ?, inventory_json = ?, save_version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(req.world_position), inv_json, new_ver, char["id"]),
        )
        if req.preferred_language:
            db.execute("UPDATE users SET preferred_language = ? WHERE id = ?", (req.preferred_language, user["id"]))
    return {"saved": True, "save_version": new_ver}
