import json
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/events", tags=["Festivals, Mini-Games & Social Achievements (v0.5.0)"])

FESTIVALS = [
    {"id": "surya_utsav", "name": "Suryanagar Solar Lantern Festival", "district": "Central Plaza", "bonus_happiness": 15},
    {"id": "science_mela", "name": "Navabharat Innovation Mela", "district": "University Quarter", "bonus_knowledge": 20},
]

TRIVIA_QUESTIONS = {
    "q_const": {"question": "What determines the Prime Minister in LIFEVERSE 2070?", "correct_answer": "democratic_election"},
    "q_solar": {"question": "Which energy powers Suryanagar's clean transit monorail?", "correct_answer": "solar"},
}


class TriviaSubmitRequest(BaseModel):
    question_id: str
    answer: str


@router.get("/festivals")
def list_festivals():
    return {"festivals": FESTIVALS, "trivia_ids": list(TRIVIA_QUESTIONS.keys())}


@router.post("/minigame/trivia")
def play_trivia_minigame(req: TriviaSubmitRequest, user: dict = Depends(get_current_user)):
    if req.question_id not in TRIVIA_QUESTIONS:
        raise HTTPException(status_code=404, detail="Trivia question not found")
    correct = req.answer.strip().lower() == TRIVIA_QUESTIONS[req.question_id]["correct_answer"]
    if not correct:
        return {"correct": False, "reward": 0, "message": "Good try! Explore the festival plaza and try another challenge."}
    with get_db() as db:
        char = db.fetchone("SELECT id, virtual_money, knowledge_points, achievements_json FROM characters WHERE user_id = ?", (user["id"],))
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        achs = json.loads(char["achievements_json"])
        if "festival_scholar" not in achs:
            achs.append("festival_scholar")
        new_bal = char["virtual_money"] + 120
        db.execute(
            "UPDATE characters SET virtual_money = ?, knowledge_points = ?, achievements_json = ? WHERE id = ?",
            (new_bal, char["knowledge_points"] + 15, json.dumps(achs), char["id"]),
        )
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'festival_minigame', 120, ?, 'Festival Trivia Win')",
            (f"tx_{secrets.token_hex(6)}", user["id"], new_bal),
        )
    return {"correct": True, "reward_virtual_money": 120, "achievement_unlocked": "festival_scholar", "balance_after": new_bal}
