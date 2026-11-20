import secrets
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user, record_audit_log, require_roles
from app.services.moderation_engine import evaluate_message

router = APIRouter(prefix="/moderation", tags=["Content Safety & Anti-Terrorism Moderation"])


class ChatCheckRequest(BaseModel):
    channel: str = Field("public_chat", pattern="^(public_chat|group_chat|private_chat|profile_bio|ugc)$")
    message: str = Field(..., min_length=1, max_length=2000)


class AbuseReportRequest(BaseModel):
    reported_user_id: str
    reason: str = Field(..., min_length=4, max_length=500)
    context_ref: str = ""


class AppealRequest(BaseModel):
    moderation_event_id: str
    reason: str = Field(..., min_length=5, max_length=1000)


class ReviewDecisionRequest(BaseModel):
    moderation_event_id: str
    appeal_decision: str = Field(..., pattern="^(approved_overturned|upheld)$")


@router.post("/check-message")
def check_and_send_message(req: ChatCheckRequest, user: dict = Depends(get_current_user)):
    now = int(time.time())
    with get_db() as db:
        u = db.fetchone("SELECT chat_restricted_until, warning_count FROM users WHERE id = ?", (user["id"],))
        if u and u["chat_restricted_until"] > now:
            raise HTTPException(status_code=403, detail="Chat privileges are temporarily restricted due to prior policy warnings.")

    result = evaluate_message(req.message, channel=req.channel)
    if result["allowed"]:
        return {"delivered": True, "moderation": result}

    event_id = f"mod_{secrets.token_hex(6)}"
    new_warning_stage = user["warning_count"]
    action_note = result["explanation"]

    with get_db() as db:
        if result["decision"] == "block":
            new_warning_stage = user["warning_count"] + 1
            if result["imminent_emergency"]:
                db.execute("UPDATE users SET warning_count = ?, is_suspended = 1 WHERE id = ?", (new_warning_stage, user["id"]))
                action_note = "Immediate protective suspension applied for credible imminent threat. Preserved for authorized review."
            elif new_warning_stage == 1:
                db.execute("UPDATE users SET warning_count = 1 WHERE id = ?", (user["id"],))
                action_note = f"Warning 1: {result['explanation']}"
            elif new_warning_stage == 2:
                restrict_until = now + 3600
                db.execute("UPDATE users SET warning_count = 2, chat_restricted_until = ? WHERE id = ?", (restrict_until, user["id"]))
                action_note = f"Warning 2: Temporary 1-hour chat restriction applied. {result['explanation']}"
            else:
                db.execute("UPDATE users SET warning_count = ?, is_suspended = 1 WHERE id = ?", (new_warning_stage, user["id"]))
                action_note = "Stage 3: Account suspended pending human moderation review. You may submit an appeal."

        db.execute(
            """INSERT INTO moderation_events
               (id, player_id, channel, message_excerpt, category, severity, decision, warning_stage, review_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                user["id"],
                req.channel,
                req.message[:180],
                result["category"],
                result["severity"],
                result["decision"],
                new_warning_stage,
                result["review_status"],
            ),
        )
    record_audit_log(user["id"], "moderation_event", "moderation_event", event_id, {"category": result["category"], "stage": new_warning_stage})
    return {"delivered": False, "moderation_event_id": event_id, "warning_stage": new_warning_stage, "message": action_note}


@router.post("/report")
def submit_abuse_report(req: AbuseReportRequest, user: dict = Depends(get_current_user)):
    rep_id = f"rep_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute(
            "INSERT INTO abuse_reports (id, reporter_id, reported_user_id, reason, context_ref) VALUES (?, ?, ?, ?, ?)",
            (rep_id, user["id"], req.reported_user_id, req.reason, req.context_ref),
        )
    return {"report_id": rep_id, "status": "open"}


@router.post("/appeal")
def submit_appeal(req: AppealRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        ev = db.fetchone("SELECT id, player_id FROM moderation_events WHERE id = ?", (req.moderation_event_id,))
        if not ev or ev["player_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Moderation event not found")
        db.execute(
            "UPDATE moderation_events SET appeal_status = 'pending', appeal_reason = ?, review_status = 'pending_review' WHERE id = ?",
            (req.reason, req.moderation_event_id),
        )
    return {"moderation_event_id": req.moderation_event_id, "appeal_status": "pending"}


@router.get("/dashboard")
def get_moderation_dashboard(user: dict = Depends(require_roles("moderator", "founder"))):
    with get_db() as db:
        events = db.fetchall("SELECT * FROM moderation_events ORDER BY created_at DESC LIMIT 100")
        reports = db.fetchall("SELECT * FROM abuse_reports ORDER BY created_at DESC LIMIT 100")
    return {"moderation_events": events, "abuse_reports": reports}


@router.post("/review-appeal")
def review_appeal(req: ReviewDecisionRequest, user: dict = Depends(require_roles("moderator", "founder"))):
    with get_db() as db:
        ev = db.fetchone("SELECT * FROM moderation_events WHERE id = ?", (req.moderation_event_id,))
        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")
        db.execute(
            "UPDATE moderation_events SET appeal_status = ?, review_status = 'reviewed' WHERE id = ?",
            (req.appeal_decision, req.moderation_event_id),
        )
        if req.appeal_decision == "approved_overturned":
            db.execute("UPDATE users SET is_suspended = 0, chat_restricted_until = 0 WHERE id = ?", (ev["player_id"],))
    record_audit_log(user["id"], "appeal_reviewed", "moderation_event", req.moderation_event_id, {"decision": req.appeal_decision})
    return {"moderation_event_id": req.moderation_event_id, "appeal_status": req.appeal_decision}
