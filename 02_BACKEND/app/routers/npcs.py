import json
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/npcs", tags=["NPCs, Landmarks & Side Activities"])

NPC_DIRECTORY = {
    "dr_meera": {
        "name": "Dr. Meera Patel",
        "role": "Quantum Lab Director",
        "landmark": "Navabharat Innovation University Dome",
        "routine": "09:00 Lab Research · 14:00 Student Mentoring · 18:00 Plaza Walk",
        "quest_title": "Calibrate Solar Sensor Array",
        "reward_money": 250,
        "reward_reputation": 15,
        "reward_knowledge": 20,
        "dialogue": {
            "en": {
                "greeting": "Welcome to the Innovation Dome! Even my coffee mug runs on solar telemetry today.",
                "help": "Thanks for helping calibrate the sensor! Suryanagar's clean grid just got smarter.",
                "joke": "Why did the quantum physicist cross the plaza? Actually, she was on both sides at once!",
            },
            "gu": {
                "greeting": "ઇનોવેશન ડોમમાં તમારું સ્વાગત છે! આજે તો મારો ચાનો કપ પણ સોલાર સેન્સરથી ચાલે છે.",
                "help": "સેન્સર કેલિબ્રેટ કરવામાં મદદ કરવા બદલ આભાર! સૂર્યનગરની ગ્રીડ વધુ સ્માર્ટ બની ગઈ.",
                "joke": "ક્વોન્ટમ વૈજ્ઞાનિક પ્લાઝા કેમ ઓળંગી? હકીકતમાં તે એકસાથે બંને બાજુ હતી!",
            },
            "hi": {
                "greeting": "इनोवेशन डोम में आपका स्वागत है! आज तो मेरा चाय का कप भी सोलर सेंसर से चलता है।",
                "help": "सेंसर कैलिब्रेट करने में मदद के लिए धन्यवाद! सूर्यनगर का ग्रिड और स्मार्ट हो गया।",
                "joke": "क्वांटम वैज्ञानिक ने प्लाज़ा क्यों पार किया? असल में वह एक साथ दोनों तरफ थी!",
            },
        },
    },
    "kaka_chai": {
        "name": "Ramesh Kaka",
        "role": "Skyline Solar Cafe Owner",
        "landmark": "Skyline Solar Cafe",
        "routine": "07:00 Masala Chai Prep · 13:00 Lunch Rush · 20:00 Community Storytelling",
        "quest_title": "Deliver Warm Chai to Plaza Volunteers",
        "reward_money": 180,
        "reward_reputation": 20,
        "reward_knowledge": 5,
        "dialogue": {
            "en": {
                "greeting": "Sit down, friend! In 2070 we have flying drones, yet nothing beats hot ginger chai.",
                "help": "You delivered every cup on time! The whole plaza is talking about your kindness.",
                "joke": "My smart-kettle tried to unionize yesterday because I asked for extra cardamom!",
            },
            "gu": {
                "greeting": "બેસો મિત્ર! ૨૦૭૦ માં ઉડતા ડ્રોન છે, પણ ગરમ આદુવાળી ચાની મજા અલગ જ છે.",
                "help": "તમે દરેક કપ સમયસર પહોંચાડ્યો! આખું પ્લાઝા તમારી મદદની વાતો કરે છે.",
                "joke": "ગઈકાલે મારી સ્માર્ટ કેટલીએ વધારે એલચી નાખવા બદલ હડતાળ પાડી દીધી!",
            },
            "hi": {
                "greeting": "बैठो दोस्त! 2070 में उड़ने वाले ड्रोन हैं, पर गरम अदरक की चाय की बात ही अलग है।",
                "help": "आपने हर कप समय पर पहुँचाया! पूरा प्लाज़ा आपकी मदद की तारीफ़ कर रहा है।",
                "joke": "कल मेरी स्मार्ट केतली ने ज़्यादा इलायची मांगने पर हड़ताल कर दी!",
            },
        },
    },
    "officer_kabir": {
        "name": "Inspector Kabir Rao",
        "role": "Civic Safety Coordinator",
        "landmark": "Suryanagar Civic Fountain",
        "routine": "08:00 Plaza Briefing · 15:00 Cyber Safety Workshop · 19:30 Evening Patrol",
        "quest_title": "Verify Public Safety Kiosk",
        "reward_money": 220,
        "reward_reputation": 25,
        "reward_knowledge": 10,
        "dialogue": {
            "en": {
                "greeting": "Good day, citizen. Safe cities are built on public trust, not just sensors.",
                "help": "Kiosk verified! Citizens appreciate someone who looks out for the community.",
                "joke": "A lost drone tried to ask me for directions to the stadium—turns out its GPS was on vacation.",
            },
            "gu": {
                "greeting": "નમસ્તે નાગરિક. સુરક્ષિત શહેર માત્ર સેન્સરથી નહીં, લોકોના વિશ્વાસથી બને છે.",
                "help": "કિઓસ્ક ચકાસાઈ ગયું! સમાજની કાળજી રાખનારા નાગરિકોની સૌ કદર કરે છે.",
                "joke": "એક ભટકેલું ડ્રોન મને સ્ટેડિયમનો રસ્તો પૂછવા આવ્યું—પછી ખબર પડી કે તેનું GPS રજા પર હતું.",
            },
            "hi": {
                "greeting": "नमस्ते नागरिक। सुरक्षित शहर केवल सेंसर से नहीं, जनता के विश्वास से बनते हैं।",
                "help": "कियोस्क सत्यापित हो गया! समुदाय का ध्यान रखने वालों का सब सम्मान करते हैं।",
                "joke": "एक भटका हुआ ड्रोन मुझसे स्टेडियम का रास्ता पूछने आया—पता चला उसका GPS छुट्टी पर था।",
            },
        },
    },
}


class NpcTalkRequest(BaseModel):
    npc_id: str
    choice: str = Field("greeting", pattern="^(greeting|joke|help)$")
    language: str | None = Field(None, pattern="^(en|gu|hi)$")


@router.get("/directory")
def list_npcs():
    return {
        "city": "Suryanagar",
        "npcs": [
            {
                "npc_id": nid,
                "name": data["name"],
                "role": data["role"],
                "landmark": data["landmark"],
                "routine": data["routine"],
                "quest_title": data["quest_title"],
            }
            for nid, data in NPC_DIRECTORY.items()
        ],
    }


@router.post("/talk")
def talk_to_npc(req: NpcTalkRequest, user: dict = Depends(get_current_user)):
    if req.npc_id not in NPC_DIRECTORY:
        raise HTTPException(status_code=404, detail="NPC not found")
    npc = NPC_DIRECTORY[req.npc_id]
    lang = req.language or user.get("preferred_language", "en")
    if lang not in ("en", "gu", "hi"):
        lang = "en"

    reply_text = npc["dialogue"][lang][req.choice]
    reward_granted = False
    new_balance = None

    with get_db() as db:
        mem = db.fetchone(
            "SELECT * FROM npc_interactions WHERE user_id = ? AND npc_id = ?",
            (user["id"], req.npc_id),
        )
        affinity = (mem["affinity_score"] if mem else 0) + (10 if req.choice == "help" else 2)
        already_completed = bool(mem["quest_completed"]) if mem else False

        if req.choice == "help" and not already_completed:
            char = db.fetchone(
                "SELECT id, virtual_money, knowledge_points, reputation_score FROM characters WHERE user_id = ?",
                (user["id"],),
            )
            if char:
                new_balance = char["virtual_money"] + npc["reward_money"]
                db.execute(
                    "UPDATE characters SET virtual_money = ?, knowledge_points = ?, reputation_score = ? WHERE id = ?",
                    (
                        new_balance,
                        char["knowledge_points"] + npc["reward_knowledge"],
                        char["reputation_score"] + npc["reward_reputation"],
                        char["id"],
                    ),
                )
                db.execute(
                    "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'npc_quest', ?, ?, ?)",
                    (f"tx_{secrets.token_hex(6)}", user["id"], npc["reward_money"], new_balance, f"NPC Quest: {npc['quest_title']}"),
                )
                reward_granted = True
                already_completed = True

        if mem:
            db.execute(
                "UPDATE npc_interactions SET affinity_score = ?, quest_completed = ?, last_dialogue_node = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (affinity, 1 if already_completed else 0, req.choice, mem["id"]),
            )
        else:
            db.execute(
                "INSERT INTO npc_interactions (id, user_id, npc_id, affinity_score, quest_completed, last_dialogue_node) VALUES (?, ?, ?, ?, ?, ?)",
                (f"npc_{secrets.token_hex(6)}", user["id"], req.npc_id, affinity, 1 if already_completed else 0, req.choice),
            )

    return {
        "npc_id": req.npc_id,
        "npc_name": npc["name"],
        "landmark": npc["landmark"],
        "language": lang,
        "reply": reply_text,
        "affinity_score": affinity,
        "quest_completed": already_completed,
        "reward_granted": reward_granted,
        "new_balance": new_balance,
    }
