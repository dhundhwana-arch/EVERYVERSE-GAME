import json
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/economy", tags=["Virtual Economy (Non-Redeemable)"])

STORE_ITEMS = {
    "apartment_starter": {"name": "Suryanagar Studio Apartment", "price": 500},
    "ev_scooter": {"name": "Solar Glide EV Scooter", "price": 350},
    "lab_kit": {"name": "Portable Science Kit", "price": 250},
}


class PurchaseRequest(BaseModel):
    item_id: str
    client_claimed_balance: int | None = Field(None, description="Ignored by server-authoritative ledger")


@router.get("/store")
def list_store():
    return {"currency_type": "non_redeemable_virtual_currency", "items": STORE_ITEMS}


@router.post("/purchase")
def purchase_item(req: PurchaseRequest, user: dict = Depends(get_current_user)):
    if req.item_id not in STORE_ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    item = STORE_ITEMS[req.item_id]
    with get_db() as db:
        char = db.fetchone("SELECT id, virtual_money, inventory_json FROM characters WHERE user_id = ?", (user["id"],))
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        if char["virtual_money"] < item["price"]:
            raise HTTPException(status_code=400, detail="Insufficient virtual currency")
        new_balance = char["virtual_money"] - item["price"]
        inv = json.loads(char["inventory_json"])
        inv.append({"item_id": req.item_id, "name": item["name"]})
        db.execute("UPDATE characters SET virtual_money = ?, inventory_json = ? WHERE id = ?", (new_balance, json.dumps(inv), char["id"]))
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'purchase', ?, ?, ?)",
            (f"tx_{secrets.token_hex(6)}", user["id"], -item["price"], new_balance, f"Purchased {item['name']}"),
        )
    return {"purchased": item["name"], "balance_after": new_balance, "server_authoritative": True}
