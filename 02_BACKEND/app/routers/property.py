import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/property", tags=["Housing, Property & Vehicles"])

PROPERTY_CATALOG = {
    "suryanagar_studio": {"name": "Suryanagar Solar Studio", "district": "Central Plaza", "price": 600},
    "univ_loft": {"name": "Innovation Dome Scholar Loft", "district": "University Quarter", "price": 1200},
    "green_villa": {"name": "Eco-Terrace Family Home", "district": "Riverfront Greens", "price": 2400},
}

VEHICLE_CATALOG = {
    "solar_scooter": {"name": "Vayu-2070 Solar Scooter", "type": "two_wheeler", "price": 300},
    "city_ev": {"name": "Surya Compact EV", "type": "car", "price": 950},
    "maglev_pass": {"name": "Annual Monorail Smart Pass", "type": "transit_pass", "price": 150},
}


class BuyAssetRequest(BaseModel):
    asset_id: str


@router.get("/catalog")
def get_catalog():
    return {"properties": PROPERTY_CATALOG, "vehicles": VEHICLE_CATALOG}


@router.post("/buy-home")
def buy_home(req: BuyAssetRequest, user: dict = Depends(get_current_user)):
    if req.asset_id not in PROPERTY_CATALOG:
        raise HTTPException(status_code=404, detail="Property not found")
    prop = PROPERTY_CATALOG[req.asset_id]
    with get_db() as db:
        char = db.fetchone("SELECT id, virtual_money FROM characters WHERE user_id = ?", (user["id"],))
        if not char or char["virtual_money"] < prop["price"]:
            raise HTTPException(status_code=400, detail="Insufficient virtual currency")
        new_bal = char["virtual_money"] - prop["price"]
        pid = f"prp_{secrets.token_hex(6)}"
        db.execute("UPDATE characters SET virtual_money = ? WHERE id = ?", (new_bal, char["id"]))
        db.execute(
            "INSERT INTO player_properties (id, user_id, property_id, property_name, district, purchase_price) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, user["id"], req.asset_id, prop["name"], prop["district"], prop["price"]),
        )
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'property_purchase', ?, ?, ?)",
            (f"tx_{secrets.token_hex(6)}", user["id"], -prop["price"], new_bal, f"Bought {prop['name']}"),
        )
    return {"owned_property_id": pid, "property_name": prop["name"], "balance_after": new_bal}


@router.post("/buy-vehicle")
def buy_vehicle(req: BuyAssetRequest, user: dict = Depends(get_current_user)):
    if req.asset_id not in VEHICLE_CATALOG:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    veh = VEHICLE_CATALOG[req.asset_id]
    with get_db() as db:
        char = db.fetchone("SELECT id, virtual_money FROM characters WHERE user_id = ?", (user["id"],))
        if not char or char["virtual_money"] < veh["price"]:
            raise HTTPException(status_code=400, detail="Insufficient virtual currency")
        new_bal = char["virtual_money"] - veh["price"]
        vid = f"veh_{secrets.token_hex(6)}"
        db.execute("UPDATE characters SET virtual_money = ? WHERE id = ?", (new_bal, char["id"]))
        db.execute(
            "INSERT INTO player_vehicles (id, user_id, vehicle_id, vehicle_name, vehicle_type, purchase_price) VALUES (?, ?, ?, ?, ?, ?)",
            (vid, user["id"], req.asset_id, veh["name"], veh["type"], veh["price"]),
        )
        db.execute(
            "INSERT INTO economy_ledger (id, user_id, tx_type, amount, balance_after, reason) VALUES (?, ?, 'vehicle_purchase', ?, ?, ?)",
            (f"tx_{secrets.token_hex(6)}", user["id"], -veh["price"], new_bal, f"Bought {veh['name']}"),
        )
    return {"owned_vehicle_id": vid, "vehicle_name": veh["name"], "balance_after": new_bal}


@router.get("/my-assets")
def my_assets(user: dict = Depends(get_current_user)):
    with get_db() as db:
        homes = db.fetchall("SELECT * FROM player_properties WHERE user_id = ?", (user["id"],))
        vehicles = db.fetchall("SELECT * FROM player_vehicles WHERE user_id = ?", (user["id"],))
    return {"properties": homes, "vehicles": vehicles}
