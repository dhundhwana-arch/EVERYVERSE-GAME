import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "02_BACKEND"))

_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.name}"
os.environ["MODERATION_CONFIG_PATH"] = str(ROOT_DIR / "06_SECURITY" / "private_moderation_config.json")

from fastapi.testclient import TestClient  # noqa: E402
from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402


class TestPatchV040(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(_TMP_DB.name):
            os.unlink(_TMP_DB.name)

    def test_01_thirty_career_registry_and_filtering(self):
        res = self.client.get("/api/v1/careers/registry")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 30)
        self.assertIn("ai_researcher", data["careers"])
        self.assertIn("cybercrime_investigator", data["careers"])
        self.assertIn("climate_scientist", data["careers"])

        sci = self.client.get("/api/v1/careers/registry?category=Science%20%26%20Research").json()
        self.assertGreaterEqual(sci["count"], 4)

    def test_02_family_wellbeing_and_founder_excluded_leaderboards(self):
        p = self.client.post("/api/v1/auth/register", json={"username": "citizen_life", "password": "Password123"}).json()
        ph = {"Authorization": f"Bearer {p['access_token']}"}
        self.client.post("/api/v1/players/character", headers=ph, json={"display_name": "Rohan", "avatar_method": "manual"})

        # Add family member and do family dinner
        fam = self.client.post("/api/v1/life/family/add", headers=ph, json={"member_name": "Ananya", "relation_type": "sibling"})
        self.assertEqual(fam.status_code, 200)
        wb = self.client.post("/api/v1/life/wellbeing/activity", headers=ph, json={"activity": "family_dinner"})
        self.assertEqual(wb.status_code, 200)
        self.assertGreater(wb.json()["happiness"], 75)

        fam_list = self.client.get("/api/v1/life/family", headers=ph).json()["family"]
        self.assertEqual(fam_list[0]["bond_score"], 65)

        # Leaderboards must have 3 separate rankings and exclude Founder accounts
        lb = self.client.get("/api/v1/life/leaderboards").json()
        self.assertIn("knowledge_leaders", lb)
        self.assertIn("public_trust_leaders", lb)
        self.assertIn("financial_leaders", lb)
        for board in (lb["knowledge_leaders"], lb["public_trust_leaders"], lb["financial_leaders"]):
            self.assertFalse(any(row["display_name"] == "divyesh_bambhaniya" for row in board))

    def test_03_property_and_vehicle_server_authoritative_ownership(self):
        p = self.client.post("/api/v1/auth/register", json={"username": "home_buyer", "password": "Password123"}).json()
        ph = {"Authorization": f"Bearer {p['access_token']}"}
        self.client.post("/api/v1/players/character", headers=ph, json={"display_name": "Meera", "avatar_method": "manual"})

        # Initial balance = 1000. Buy studio (600) + solar scooter (300) = 100 left
        h = self.client.post("/api/v1/property/buy-home", headers=ph, json={"asset_id": "suryanagar_studio"})
        self.assertEqual(h.status_code, 200)
        self.assertEqual(h.json()["balance_after"], 400)

        v = self.client.post("/api/v1/property/buy-vehicle", headers=ph, json={"asset_id": "solar_scooter"})
        self.assertEqual(v.status_code, 200)
        self.assertEqual(v.json()["balance_after"], 100)

        # Insufficient balance must fail (green_villa = 2400)
        fail_buy = self.client.post("/api/v1/property/buy-home", headers=ph, json={"asset_id": "green_villa"})
        self.assertEqual(fail_buy.status_code, 400)

        assets = self.client.get("/api/v1/property/my-assets", headers=ph).json()
        self.assertEqual(len(assets["properties"]), 1)
        self.assertEqual(len(assets["vehicles"]), 1)


if __name__ == "__main__":
    unittest.main()
