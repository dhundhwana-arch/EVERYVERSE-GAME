import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user, record_audit_log

router = APIRouter(prefix="/justice", tags=["Law, Police & Judiciary (v0.5.0)"])


class FileCaseRequest(BaseModel):
    case_type: str = Field(..., pattern="^(civic_dispute|cyber_fraud_report|public_safety|contract_breach)$")
    summary: str = Field(..., min_length=8, max_length=500)


class VerdictRequest(BaseModel):
    case_id: str
    verdict: str = Field(..., pattern="^(resolved_mediated|upheld_penalty|dismissed_no_evidence)$")


@router.post("/cases/file")
def file_civic_case(req: FileCaseRequest, user: dict = Depends(get_current_user)):
    case_id = f"cas_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute(
            "INSERT INTO civic_cases (id, filed_by_user_id, case_type, summary, status) VALUES (?, ?, ?, ?, 'open')",
            (case_id, user["id"], req.case_type, req.summary),
        )
    return {"case_id": case_id, "status": "open", "case_type": req.case_type}


@router.post("/cases/verdict")
def deliver_verdict(req: VerdictRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        case = db.fetchone("SELECT * FROM civic_cases WHERE id = ?", (req.case_id,))
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        if case["status"] == "closed":
            raise HTTPException(status_code=409, detail="Case already closed")
        db.execute("UPDATE civic_cases SET status = 'closed', verdict = ? WHERE id = ?", (req.verdict, req.case_id))
        db.execute("UPDATE characters SET reputation_score = reputation_score + 10 WHERE user_id = ?", (user["id"],))
    record_audit_log(user["id"], "court_verdict", "civic_case", req.case_id, {"verdict": req.verdict})
    return {"case_id": req.case_id, "status": "closed", "verdict": req.verdict}


@router.get("/cases")
def list_cases():
    with get_db() as db:
        rows = db.fetchall("SELECT id, case_type, summary, status, verdict, created_at FROM civic_cases ORDER BY created_at DESC LIMIT 50")
    return {"cases": rows}
