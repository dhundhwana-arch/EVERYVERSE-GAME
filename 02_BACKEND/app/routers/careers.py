import json
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user, record_audit_log

router = APIRouter(prefix="/careers", tags=["Careers & National Leadership"])

CAREER_REGISTRY = {
    "scientist": {
        "title": "Scientist / Researcher",
        "category": "Science & Research",
        "stages": ["Research Fundamentals", "Scientific Problem Solving", "Research Proposal"],
        "reward_money": 800,
        "reward_knowledge": 40,
        "reward_reputation": 25,
    },
    "civil_admin": {
        "title": "Civil Administrator (IAS-Inspired)",
        "category": "Government & Administration",
        "stages": ["Constitutional Literacy", "Administrative Case Study", "Civil Service Interview"],
        "reward_money": 750,
        "reward_knowledge": 35,
        "reward_reputation": 35,
    },
    "business_owner": {
        "title": "Business Owner / Entrepreneur",
        "category": "Business & Finance",
        "stages": ["Market Feasibility Plan", "Financial Budgeting", "Operations Launch"],
        "reward_money": 1100,
        "reward_knowledge": 25,
        "reward_reputation": 20,
    },
}


class CareerSelectRequest(BaseModel):
    career_id: str


class TaskSubmitRequest(BaseModel):
    task_id: str
    answer_score: int = Field(..., ge=0, le=100)


class CandidateRegisterRequest(BaseModel):
    election_id: str
    public_trust: int = Field(..., ge=0, le=100)
    governance_score: int = Field(..., ge=0, le=100)
    integrity_score: int = Field(..., ge=0, le=100)


@router.get("/registry")
def list_careers():
    return {"careers": CAREER_REGISTRY, "onboarding_choices": ["explore_all", "not_sure_yet", "create_own_path", "just_explore_world"]}


@router.post("/select")
def select_career(req: CareerSelectRequest, user: dict = Depends(get_current_user)):
    if req.career_id not in CAREER_REGISTRY:
        raise HTTPException(status_code=404, detail="Career not found in registry")
    spec = CAREER_REGISTRY[req.career_id]
    task_id = f"tsk_{secrets.token_hex(6)}"
    deadline = int(time.time()) + 72 * 3600
    with get_db() as db:
        db.execute("UPDATE characters SET active_career_id = ? WHERE user_id = ?", (req.career_id, user["id"]))
        db.execute(
            "INSERT INTO career_tasks (id, user_id, career_id, title, stage, status, deadline_epoch) VALUES (?, ?, ?, ?, 1, 'assigned', ?)",
            (task_id, user["id"], req.career_id, spec["stages"][0], deadline),
        )
    return {"active_career_id": req.career_id, "assigned_task": {"task_id": task_id, "title": spec["stages"][0], "stage": 1, "deadline_epoch": deadline}}


@router.post("/submit-task")
def submit_task(req: TaskSubmitRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        task = db.fetchone("SELECT * FROM career_tasks WHERE id = ? AND user_id = ?", (req.task_id, user["id"]))
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task["status"] == "completed":
            raise HTTPException(status_code=409, detail="Task already completed")
        attempts = task["attempts"] + 1
        passed = req.answer_score >= 60
        if passed:
            spec = CAREER_REGISTRY[task["career_id"]]
            char = db.fetchone("SELECT id, virtual_money, knowledge_points, reputation_score, skills_json FROM characters WHERE user_id = ?", (user["id"],))
            skills = json.loads(char["skills_json"])
            skills[task["career_id"]] = skills.get(task["career_id"], 0) + 1
            new_balance = char["virtual_money"] + spec["reward_money"]
            db.execute(
                "UPDATE career_tasks SET status = 'completed', attempts = ?, score = ?, feedback = 'Qualification milestone passed.' WHERE id = ?",
                (attempts, req.answer_score, task["id"]),
            )
            db.execute(
                "UPDATE characters SET virtual_money = ?, knowledge_points = ?, reputation_score = ?, skills_json = ? WHERE id = ?",
                (
                    new_balance,
                    char["knowledge_points"] + spec["reward_knowledge"],
                    char["reputation_score"] + spec["reward_reputation"],
                    json.dumps(skills),
                    char["id"],
                ),
            )
            db.execute(
                "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'career_reward', ?, ?, ?)",
                (f"tx_{secrets.token_hex(6)}", user["id"], spec["reward_money"], new_balance, f"Completed {task['title']}"),
            )

            next_stage = task["stage"] + 1
            next_task = None
            career_mastered = False
            if next_stage <= len(spec["stages"]):
                next_task_id = f"tsk_{secrets.token_hex(6)}"
                next_title = spec["stages"][next_stage - 1]
                deadline = int(time.time()) + 72 * 3600
                db.execute(
                    "INSERT INTO career_tasks (id, user_id, career_id, title, stage, status, deadline_epoch) VALUES (?, ?, ?, ?, ?, 'assigned', ?)",
                    (next_task_id, user["id"], task["career_id"], next_title, next_stage, deadline),
                )
                next_task = {"task_id": next_task_id, "title": next_title, "stage": next_stage, "deadline_epoch": deadline}
            else:
                career_mastered = True

            return {
                "passed": True,
                "skills_preserved": True,
                "new_balance": new_balance,
                "completed_stage": task["stage"],
                "career_mastered": career_mastered,
                "next_task": next_task,
                "feedback": "Qualification milestone passed.",
            }
        else:
            db.execute(
                "UPDATE career_tasks SET status = 'retry_available', attempts = ?, score = ?, feedback = ? WHERE id = ?",
                (attempts, req.answer_score, "Your journey is not over! Want to try again, improve your skills or explore another career?", task["id"]),
            )
            return {
                "passed": False,
                "skills_preserved": True,
                "message": "Your journey is not over! Want to try again, improve your skills or explore another career?",
                "options": ["retry_task", "additional_training", "different_task", "change_career"],
            }


@router.post("/elections/create")
def create_election(title: str = "National Prime Minister Election", user: dict = Depends(get_current_user)):
    el_id = f"el_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute("INSERT INTO elections (id, country_name, title, status) VALUES (?, 'Navabharat Confederation', ?, 'open')", (el_id, title))
    return {"election_id": el_id, "title": title, "status": "open"}


@router.post("/elections/register-candidate")
def register_candidate(req: CandidateRegisterRequest, user: dict = Depends(get_current_user)):
    cand_id = f"cnd_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute(
            "INSERT INTO election_candidates (id, election_id, user_id, public_trust, governance_score, integrity_score) VALUES (?, ?, ?, ?, ?, ?)",
            (cand_id, req.election_id, user["id"], req.public_trust, req.governance_score, req.integrity_score),
        )
    return {"candidate_id": cand_id, "election_id": req.election_id}


@router.post("/elections/{election_id}/vote/{candidate_id}")
def cast_vote(election_id: str, candidate_id: str, user: dict = Depends(get_current_user)):
    vote_id = f"vot_{secrets.token_hex(6)}"
    with get_db() as db:
        election = db.fetchone("SELECT status FROM elections WHERE id = ?", (election_id,))
        if not election or election["status"] != "open":
            raise HTTPException(status_code=400, detail="Election is not open")
        cand = db.fetchone("SELECT id, votes FROM election_candidates WHERE id = ? AND election_id = ?", (candidate_id, election_id))
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        existing_vote = db.fetchone(
            "SELECT id FROM election_votes WHERE election_id = ? AND voter_user_id = ?",
            (election_id, user["id"]),
        )
        if existing_vote:
            raise HTTPException(status_code=409, detail="Duplicate vote rejected: one vote per player per election.")
        try:
            db.execute(
                "INSERT INTO election_votes (id, election_id, voter_user_id, candidate_id) VALUES (?, ?, ?, ?)",
                (vote_id, election_id, user["id"], candidate_id),
            )
        except Exception as exc:
            raise HTTPException(status_code=409, detail="Duplicate vote rejected by database constraint.") from exc
        db.execute("UPDATE election_candidates SET votes = ? WHERE id = ?", (cand["votes"] + 1, candidate_id))
    return {"voted_for": candidate_id, "vote_id": vote_id}


@router.post("/elections/{election_id}/finalize")
def finalize_election(election_id: str, user: dict = Depends(get_current_user)):
    with get_db() as db:
        candidates = db.fetchall("SELECT * FROM election_candidates WHERE election_id = ?", (election_id,))
        if not candidates:
            raise HTTPException(status_code=400, detail="No candidates registered")
        ranked = sorted(
            candidates,
            key=lambda c: (c["votes"] * 10 + c["public_trust"] + c["governance_score"] + c["integrity_score"]),
            reverse=True,
        )
        pm = ranked[0]
        db.execute("UPDATE elections SET status = 'completed', winner_user_id = ? WHERE id = ?", (pm["user_id"], election_id))
        db.execute("UPDATE election_candidates SET assigned_office = 'Prime Minister' WHERE id = ?", (pm["id"],))
        fallback_offices = ["Deputy Prime Minister", "Finance Minister", "Home Minister", "Senior Policy Advisor"]
        for idx, runner in enumerate(ranked[1:]):
            office = fallback_offices[idx] if idx < len(fallback_offices) else "Parliament Leader"
            db.execute("UPDATE election_candidates SET assigned_office = ? WHERE id = ?", (office, runner["id"]))
    record_audit_log(user["id"], "election_finalized", "election", election_id, {"pm_user_id": pm["user_id"]})
    return {"prime_minister_user_id": pm["user_id"], "cabinet_appointments_assigned": len(ranked)}
