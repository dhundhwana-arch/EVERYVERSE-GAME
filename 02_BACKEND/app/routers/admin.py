from fastapi import APIRouter, Depends

from app.config import OFFICIAL_BRANDING
from app.database import get_db
from app.security import require_roles

router = APIRouter(prefix="/admin", tags=["Founder Dashboard"])


@router.get("/overview")
def founder_overview(user: dict = Depends(require_roles("founder"))):
    with get_db() as db:
        players = db.fetchone("SELECT COUNT(*) AS cnt FROM users")
        chars = db.fetchone("SELECT COUNT(*) AS cnt FROM characters")
        mod_events = db.fetchone("SELECT COUNT(*) AS cnt FROM moderation_events")
        open_reports = db.fetchone("SELECT COUNT(*) AS cnt FROM abuse_reports WHERE status = 'open'")
        recent_audits = db.fetchall("SELECT id, actor_id, action, target_type, target_id, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 25")
    return {
        "branding": OFFICIAL_BRANDING,
        "founder": user["username"],
        "total_users": players["cnt"] if players else 0,
        "total_characters": chars["cnt"] if chars else 0,
        "moderation_events": mod_events["cnt"] if mod_events else 0,
        "open_abuse_reports": open_reports["cnt"] if open_reports else 0,
        "recent_audit_logs": recent_audits,
    }
