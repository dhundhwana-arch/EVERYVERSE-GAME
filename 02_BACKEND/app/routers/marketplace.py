import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/marketplace", tags=["Virtual Services & Crafted Marketplace (v0.6.0)"])


class ListingRequest(BaseModel):
    listing_type: str = Field(..., pattern="^(tutoring_service|business_mentoring|crafted_furniture|custom_outfit)$")
    title: str = Field(..., min_length=4, max_length=60)
    price_virtual: int = Field(..., ge=50, le=5000)


class BuyListingRequest(BaseModel):
    listing_id: str


@router.post("/listings/create")
def create_listing(req: ListingRequest, user: dict = Depends(get_current_user)):
    lid = f"mkt_{secrets.token_hex(6)}"
    with get_db() as db:
        db.execute(
            "INSERT INTO marketplace_listings (id, seller_user_id, listing_type, title, price_virtual, status) VALUES (?, ?, ?, ?, ?, 'open')",
            (lid, user["id"], req.listing_type, req.title, req.price_virtual),
        )
    return {"listing_id": lid, "title": req.title, "price_virtual": req.price_virtual, "currency_type": "non_redeemable_virtual_currency"}


@router.post("/listings/buy")
def buy_listing(req: BuyListingRequest, user: dict = Depends(get_current_user)):
    with get_db() as db:
        item = db.fetchone("SELECT * FROM marketplace_listings WHERE id = ? AND status = 'open'", (req.listing_id,))
        if not item:
            raise HTTPException(status_code=404, detail="Listing not available")
        if item["seller_user_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="Cannot buy your own listing")
        buyer = db.fetchone("SELECT id, virtual_money FROM characters WHERE user_id = ?", (user["id"],))
        seller = db.fetchone("SELECT id, virtual_money FROM characters WHERE user_id = ?", (item["seller_user_id"],))
        if not buyer or buyer["virtual_money"] < item["price_virtual"]:
            raise HTTPException(status_code=400, detail="Insufficient virtual currency")
        buyer_bal = buyer["virtual_money"] - item["price_virtual"]
        seller_bal = (seller["virtual_money"] if seller else 0) + item["price_virtual"]
        db.execute("UPDATE characters SET virtual_money = ? WHERE id = ?", (buyer_bal, buyer["id"]))
        if seller:
            db.execute("UPDATE characters SET virtual_money = ? WHERE id = ?", (seller_bal, seller["id"]))
        db.execute("UPDATE marketplace_listings SET status = 'sold', buyer_user_id = ? WHERE id = ?", (user["id"], item["id"]))
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'marketplace_buy', ?, ?, ?)",
            (f"tx_{secrets.token_hex(6)}", user["id"], -item["price_virtual"], buyer_bal, f"Bought {item['title']}"),
        )
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'marketplace_sell', ?, ?, ?)",
            (f"tx_{secrets.token_hex(6)}", item["seller_user_id"], item["price_virtual"], seller_bal, f"Sold {item['title']}"),
        )
    return {"listing_id": item["id"], "status": "sold", "buyer_balance_after": buyer_bal}
