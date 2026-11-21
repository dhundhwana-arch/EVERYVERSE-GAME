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


class TestPatchV05AndV06(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(_TMP_DB.name):
            os.unlink(_TMP_DB.name)

    def _mk_player(self, username: str) -> dict:
        reg = self.client.post("/api/v1/auth/register", json={"username": username, "password": "Password123"}).json()
        h = {"Authorization": f"Bearer {reg['access_token']}"}
        self.client.post("/api/v1/players/character", headers=h, json={"display_name": username, "avatar_method": "manual"})
        return h

    def test_01_justice_case_filing_and_verdict(self):
        h = self._mk_player("judge_arya")
        f = self.client.post("/api/v1/justice/cases/file", headers=h, json={"case_type": "civic_dispute", "summary": "Solar lane parking dispute near Innovation Dome"})
        self.assertEqual(f.status_code, 200)
        cid = f.json()["case_id"]

        v = self.client.post("/api/v1/justice/cases/verdict", headers=h, json={"case_id": cid, "verdict": "resolved_mediated"})
        self.assertEqual(v.status_code, 200)
        self.assertEqual(v.json()["status"], "closed")

        # Re-closing must fail with 409
        v2 = self.client.post("/api/v1/justice/cases/verdict", headers=h, json={"case_id": cid, "verdict": "upheld_penalty"})
        self.assertEqual(v2.status_code, 409)

    def test_02_business_startup_and_risk_return_cycle(self):
        h = self._mk_player("founder_kajal")
        st = self.client.post("/api/v1/business/startup/create", headers=h, json={"business_name": "Surya Grid Co", "sector": "clean_energy", "initial_capital": 500})
        self.assertEqual(st.status_code, 200)
        self.assertEqual(st.json()["balance_after"], 500)
        biz_id = st.json()["business_id"]

        cyc = self.client.post("/api/v1/business/startup/run-cycle", headers=h, json={"business_id": biz_id})
        self.assertEqual(cyc.status_code, 200)
        self.assertEqual(cyc.json()["net_virtual_delta"], 60)
        self.assertEqual(cyc.json()["balance_after"], 560)

        # Deep tech loss risk test
        dt = self.client.post("/api/v1/business/startup/create", headers=h, json={"business_name": "NanoFab Risk", "sector": "deep_tech", "initial_capital": 200}).json()
        loss = self.client.post("/api/v1/business/startup/run-cycle", headers=h, json={"business_id": dt["business_id"]}).json()
        self.assertLess(loss["net_virtual_delta"], 0)

    def test_03_festivals_trivia_and_research_breakthrough(self):
        h = self._mk_player("scholar_dev")
        triv = self.client.post("/api/v1/events/minigame/trivia", headers=h, json={"question_id": "q_solar", "answer": "solar"})
        self.assertEqual(triv.status_code, 200)
        self.assertTrue(triv.json()["correct"])
        self.assertEqual(triv.json()["achievement_unlocked"], "festival_scholar")

        proj = self.client.post("/api/v1/research/projects/start", headers=h, json={"domain": "semiconductors", "title": "2nm Photonic Chip"}).json()
        c1 = self.client.post("/api/v1/research/projects/contribute", headers=h, json={"project_id": proj["project_id"], "progress_increment": 50}).json()
        self.assertEqual(c1["status"], "active")
        c2 = self.client.post("/api/v1/research/projects/contribute", headers=h, json={"project_id": proj["project_id"], "progress_increment": 50}).json()
        self.assertEqual(c2["status"], "published")

    def test_04_virtual_services_marketplace_trade(self):
        seller_h = self._mk_player("mentor_raj")
        buyer_h = self._mk_player("student_diya")

        lst = self.client.post("/api/v1/marketplace/listings/create", headers=seller_h, json={"listing_type": "tutoring_service", "title": "Civil Service Exam Mentoring", "price_virtual": 200}).json()
        # Self-buy must be rejected
        self_buy = self.client.post("/api/v1/marketplace/listings/buy", headers=seller_h, json={"listing_id": lst["listing_id"]})
        self.assertEqual(self_buy.status_code, 400)

        # Buyer purchases service -> 1000 - 200 = 800
        buy = self.client.post("/api/v1/marketplace/listings/buy", headers=buyer_h, json={"listing_id": lst["listing_id"]})
        self.assertEqual(buy.status_code, 200)
        self.assertEqual(buy.json()["buyer_balance_after"], 800)


if __name__ == "__main__":
    unittest.main()
