import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/business", tags=["Business Startups & Virtual Investment (v0.5.0)"])

MARKET_FACTORS = {
    "clean_energy": {"label": "Solar & Clean Energy", "return_pct": 12, "risk_note": "Moderate return with weather variance"},
    "edtech": {"label": "Gujarati/Hindi EdTech", "return_pct": 8, "risk_note": "Steady educational demand"},
    "deep_tech": {"label": "Semiconductor & AI Lab", "return_pct": -5, "risk_note": "High R&D volatility — losses possible"},
}


class StartupRequest(BaseModel):
    business_name: str = Field(..., min_length=3, max_length=50)
    sector: str = Field(..., pattern="^(clean_energy|edtech|deep_tech)$")
    initial_capital: int = Field(..., ge=200, le=5000)


class CycleRequest(BaseModel):
    business_id: str


@router.post("/startup/create")
def create_startup(req: StartupRequest, user: dict = Depends(get_current_user)):
    biz_id = f"biz_{secrets.token_hex(6)}"
    with get_db() as db:
        char = db.fetchone("SELECT id, virtual_money FROM characters WHERE user_id = ?", (user["id"],))
        if not char or char["virtual_money"] < req.initial_capital:
            raise HTTPException(status_code=400, detail="Insufficient virtual currency for startup capital")
        new_bal = char["virtual_money"] - req.initial_capital
        db.execute("UPDATE characters SET virtual_money = ? WHERE id = ?", (new_bal, char["id"]))
        db.execute(
            "INSERT INTO player_businesses (id, owner_user_id, business_name, sector, capital_invested) VALUES (?, ?, ?, ?, ?)",
            (biz_id, user["id"], req.business_name, req.sector, req.initial_capital),
        )
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'startup_capital', ?, ?, ?)",
            (f"tx_{secrets.token_hex(6)}", user["id"], -req.initial_capital, new_bal, f"Founded {req.business_name}"),
        )
    return {"business_id": biz_id, "business_name": req.business_name, "balance_after": new_bal, "currency_type": "non_redeemable_virtual_currency"}


@router.post("/startup/run-cycle")
def run_business_cycle(req: CycleRequest, user: dict = Depends(get_current_user)):
    """Simulates a quarterly virtual market cycle with realistic profit OR loss risk."""
    with get_db() as db:
        biz = db.fetchone("SELECT * FROM player_businesses WHERE id = ? AND owner_user_id = ?", (req.business_id, user["id"]))
        if not biz:
            raise HTTPException(status_code=404, detail="Business not found")
        factor = MARKET_FACTORS[biz["sector"]]
        net_delta = int(biz["capital_invested"] * factor["return_pct"] / 100)
        char = db.fetchone("SELECT id, virtual_money FROM characters WHERE user_id = ?", (user["id"],))
        new_bal = max(0, char["virtual_money"] + net_delta)
        db.execute("UPDATE characters SET virtual_money = ? WHERE id = ?", (new_bal, char["id"]))
        db.execute("UPDATE player_businesses SET revenue_total = revenue_total + ? WHERE id = ?", (net_delta, biz["id"]))
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'business_cycle', ?, ?, ?)",
            (f"tx_{secrets.token_hex(6)}", user["id"], net_delta, new_bal, f"Cycle result ({biz['sector']})"),
        )
    return {"business_id": biz["id"], "net_virtual_delta": net_delta, "balance_after": new_bal, "risk_note": factor["risk_note"]}
