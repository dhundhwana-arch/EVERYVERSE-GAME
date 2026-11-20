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


class TestPatchV030(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(_TMP_DB.name):
            os.unlink(_TMP_DB.name)

    def test_01_npc_directory_and_multilingual_dialogue(self):
        dir_res = self.client.get("/api/v1/npcs/directory")
        self.assertEqual(dir_res.status_code, 200)
        npcs = dir_res.json()["npcs"]
        self.assertGreaterEqual(len(npcs), 3)

        reg = self.client.post("/api/v1/auth/register", json={"username": "npc_explorer", "password": "Password123", "preferred_language": "gu"}).json()
        headers = {"Authorization": f"Bearer {reg['access_token']}"}
        self.client.post("/api/v1/players/character", headers=headers, json={"display_name": "Kiran", "avatar_method": "manual"})

        # Gujarati greeting with Dr. Meera
        g = self.client.post("/api/v1/npcs/talk", headers=headers, json={"npc_id": "dr_meera", "choice": "greeting", "language": "gu"})
        self.assertEqual(g.status_code, 200)
        self.assertIn("ઇનોવેશન ડોમમાં", g.json()["reply"])
        self.assertEqual(g.json()["affinity_score"], 2)

        # Hindi joke with Ramesh Kaka
        j = self.client.post("/api/v1/npcs/talk", headers=headers, json={"npc_id": "kaka_chai", "choice": "joke", "language": "hi"})
        self.assertEqual(j.status_code, 200)
        self.assertIn("स्मार्ट केतली", j.json()["reply"])

    def test_02_npc_side_quest_reward_and_idempotency(self):
        reg = self.client.post("/api/v1/auth/register", json={"username": "quest_helper", "password": "Password123"}).json()
        headers = {"Authorization": f"Bearer {reg['access_token']}"}
        self.client.post("/api/v1/players/character", headers=headers, json={"display_name": "Neha", "avatar_method": "manual"})

        # First quest completion grants reward (1000 + 250 = 1250)
        q1 = self.client.post("/api/v1/npcs/talk", headers=headers, json={"npc_id": "dr_meera", "choice": "help", "language": "en"})
        self.assertEqual(q1.status_code, 200)
        self.assertTrue(q1.json()["reward_granted"])
        self.assertEqual(q1.json()["new_balance"], 1250)

        # Second attempt on same NPC quest must NOT double-pay (anti-farming)
        q2 = self.client.post("/api/v1/npcs/talk", headers=headers, json={"npc_id": "dr_meera", "choice": "help", "language": "en"})
        self.assertEqual(q2.status_code, 200)
        self.assertFalse(q2.json()["reward_granted"])
        self.assertIsNone(q2.json()["new_balance"])

    def test_03_health_reports_v0_3_0(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["version"], "0.3.0")


if __name__ == "__main__":
    unittest.main()
