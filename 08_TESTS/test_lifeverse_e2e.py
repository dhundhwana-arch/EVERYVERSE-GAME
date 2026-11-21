import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "02_BACKEND"
sys.path.insert(0, str(BACKEND_DIR))

_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.name}"
os.environ["MODERATION_CONFIG_PATH"] = str(ROOT_DIR / "06_SECURITY" / "private_moderation_config.json")

from fastapi.testclient import TestClient  # noqa: E402
from app.bootstrap_founder import provision_founder  # noqa: E402
from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.security import compute_totp  # noqa: E402


class TestLifeverse2070E2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(_TMP_DB.name):
            os.unlink(_TMP_DB.name)

    def test_01_health_and_branding(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["branding"], "CREATED BY DIVYESH BAMBHANIYA")

    def test_02_auth_cloud_save_and_restore(self):
        reg = self.client.post("/api/v1/auth/register", json={"username": "aarav_test", "email": "aarav@example.com", "password": "StrongPassword123", "preferred_language": "gu"})
        self.assertEqual(reg.status_code, 200)
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        bad_char = self.client.post("/api/v1/players/character", headers=headers, json={"display_name": "Aarav", "avatar_method": "photo_reference", "photo_consent_granted": False})
        self.assertEqual(bad_char.status_code, 400)

        char = self.client.post("/api/v1/players/character", headers=headers, json={"display_name": "Aarav", "avatar_method": "manual", "avatar_config": {"hair": "short"}})
        self.assertEqual(char.status_code, 200)

        save_res = self.client.put("/api/v1/players/save", headers=headers, json={"world_position": {"x": 42, "y": 0, "z": 18, "district": "Navabharat University"}})
        self.assertEqual(save_res.status_code, 200)
        self.assertEqual(save_res.json()["save_version"], 2)

        login = self.client.post("/api/v1/auth/login", json={"username": "aarav_test", "password": "StrongPassword123"})
        self.assertEqual(login.status_code, 200)
        new_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        loaded = self.client.get("/api/v1/players/save", headers=new_headers)
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["world_position"]["district"], "Navabharat University")

    def test_03_career_task_zero_loss_retry_and_economy_anticheat(self):
        reg = self.client.post("/api/v1/auth/register", json={"username": "priya_sci", "password": "Password123", "preferred_language": "hi"})
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        self.client.post("/api/v1/players/character", headers=headers, json={"display_name": "Dr. Priya", "avatar_method": "manual"})

        sel = self.client.post("/api/v1/careers/select", headers=headers, json={"career_id": "scientist"})
        self.assertEqual(sel.status_code, 200)
        task_id = sel.json()["assigned_task"]["task_id"]

        fail_res = self.client.post("/api/v1/careers/submit-task", headers=headers, json={"task_id": task_id, "answer_score": 45})
        self.assertEqual(fail_res.status_code, 200)
        self.assertFalse(fail_res.json()["passed"])
        self.assertTrue(fail_res.json()["skills_preserved"])

        pass_res = self.client.post("/api/v1/careers/submit-task", headers=headers, json={"task_id": task_id, "answer_score": 88})
        self.assertTrue(pass_res.json()["passed"])
        self.assertEqual(pass_res.json()["new_balance"], 1800)

        buy = self.client.post("/api/v1/economy/purchase", headers=headers, json={"item_id": "apartment_starter", "client_claimed_balance": 9999999})
        self.assertEqual(buy.status_code, 200)
        self.assertEqual(buy.json()["balance_after"], 1300)

    def test_04_fair_pm_election_and_cabinet_fallback(self):
        u1 = self.client.post("/api/v1/auth/register", json={"username": "cand_one", "password": "Password123"}).json()["access_token"]
        u2 = self.client.post("/api/v1/auth/register", json={"username": "cand_two", "password": "Password123"}).json()["access_token"]
        h1, h2 = {"Authorization": f"Bearer {u1}"}, {"Authorization": f"Bearer {u2}"}

        el_id = self.client.post("/api/v1/careers/elections/create", headers=h1).json()["election_id"]
        c1 = self.client.post("/api/v1/careers/elections/register-candidate", headers=h1, json={"election_id": el_id, "public_trust": 90, "governance_score": 85, "integrity_score": 95}).json()["candidate_id"]
        c2 = self.client.post("/api/v1/careers/elections/register-candidate", headers=h2, json={"election_id": el_id, "public_trust": 80, "governance_score": 82, "integrity_score": 88}).json()["candidate_id"]

        self.client.post(f"/api/v1/careers/elections/{el_id}/vote/{c1}", headers=h1)
        self.client.post(f"/api/v1/careers/elections/{el_id}/vote/{c2}", headers=h2)

        fin = self.client.post(f"/api/v1/careers/elections/{el_id}/finalize", headers=h1)
        self.assertEqual(fin.status_code, 200)
        self.assertEqual(fin.json()["cabinet_appointments_assigned"], 2)

    def test_05_multilingual_moderation_and_founder_rbac(self):
        p_tok = self.client.post("/api/v1/auth/register", json={"username": "mod_tester", "password": "Password123"}).json()["access_token"]
        # Provision Founder strictly server-side with MFA
        f_info = provision_founder("founder_secure_e2e", "FounderSecret123", email="founder@lifeverse2070.example")
        f_login = self.client.post(
            "/api/v1/auth/login",
            json={"username": "founder_secure_e2e", "password": "FounderSecret123", "totp_code": compute_totp(f_info["totp_secret"])},
        ).json()
        ph, fh = {"Authorization": f"Bearer {p_tok}"}, {"Authorization": f"Bearer {f_login['access_token']}"}

        edu = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "I am studying historical counter-terrorism awareness for my GPSC exam."})
        self.assertTrue(edu.json()["delivered"])

        w1 = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "a t a n k w a d i sangathan ma joday"})
        self.assertFalse(w1.json()["delivered"])
        self.assertEqual(w1.json()["warning_stage"], 1)

        forbidden = self.client.get("/api/v1/admin/overview", headers=ph)
        self.assertEqual(forbidden.status_code, 403)

        ov = self.client.get("/api/v1/admin/overview", headers=fh)
        self.assertEqual(ov.status_code, 200)
        self.assertEqual(ov.json()["branding"], "CREATED BY DIVYESH BAMBHANIYA")
        mod_dash = self.client.get("/api/v1/moderation/dashboard", headers=fh)
        self.assertEqual(mod_dash.status_code, 200)
        self.assertGreaterEqual(len(mod_dash.json()["moderation_events"]), 1)


if __name__ == "__main__":
    unittest.main()
