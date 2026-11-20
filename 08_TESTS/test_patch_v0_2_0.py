import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "02_BACKEND"))
sys.path.insert(0, str(ROOT_DIR / "03_DATABASE" / "backup"))

_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.name}"
os.environ["MODERATION_CONFIG_PATH"] = str(ROOT_DIR / "06_SECURITY" / "private_moderation_config.json")

from fastapi.testclient import TestClient  # noqa: E402
from backup_and_restore import create_sqlite_backup, restore_sqlite_backup  # noqa: E402
from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402


class TestPatchV020(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(_TMP_DB.name):
            os.unlink(_TMP_DB.name)

    def _register_and_char(self, username: str, lang: str = "en") -> tuple[str, str, dict]:
        reg = self.client.post("/api/v1/auth/register", json={"username": username, "password": "Password123", "preferred_language": lang}).json()
        tok = reg["access_token"]
        headers = {"Authorization": f"Bearer {tok}"}
        self.client.post("/api/v1/players/character", headers=headers, json={"display_name": username, "avatar_method": "manual"})
        return reg["user_id"], tok, headers

    def test_01_duplicate_vote_rejected(self):
        _, _, h1 = self._register_and_char("voter_one")
        _, _, h2 = self._register_and_char("cand_alpha")
        el_id = self.client.post("/api/v1/careers/elections/create", headers=h1).json()["election_id"]
        c_id = self.client.post("/api/v1/careers/elections/register-candidate", headers=h2, json={"election_id": el_id, "public_trust": 80, "governance_score": 80, "integrity_score": 90}).json()["candidate_id"]

        v1 = self.client.post(f"/api/v1/careers/elections/{el_id}/vote/{c_id}", headers=h1)
        self.assertEqual(v1.status_code, 200)
        v2 = self.client.post(f"/api/v1/careers/elections/{el_id}/vote/{c_id}", headers=h1)
        self.assertEqual(v2.status_code, 409)

    def test_02_career_stages_1_to_3_progression(self):
        _, _, headers = self._register_and_char("stage_runner")
        sel = self.client.post("/api/v1/careers/select", headers=headers, json={"career_id": "civil_admin"}).json()
        t1 = sel["assigned_task"]["task_id"]

        r1 = self.client.post("/api/v1/careers/submit-task", headers=headers, json={"task_id": t1, "answer_score": 75}).json()
        self.assertEqual(r1["completed_stage"], 1)
        self.assertFalse(r1["career_mastered"])
        t2 = r1["next_task"]["task_id"]

        r2 = self.client.post("/api/v1/careers/submit-task", headers=headers, json={"task_id": t2, "answer_score": 82}).json()
        self.assertEqual(r2["completed_stage"], 2)
        t3 = r2["next_task"]["task_id"]

        r3 = self.client.post("/api/v1/careers/submit-task", headers=headers, json={"task_id": t3, "answer_score": 91}).json()
        self.assertEqual(r3["completed_stage"], 3)
        self.assertTrue(r3["career_mastered"])
        self.assertIsNone(r3["next_task"])

    def test_03_social_friend_accept_party_and_websocket(self):
        u1, t1, h1 = self._register_and_char("social_a")
        u2, t2, h2 = self._register_and_char("social_b")

        self.client.post("/api/v1/social/friends/request", headers=h1, json={"target_user_id": u2})
        acc = self.client.post("/api/v1/social/friends/accept", headers=h2, json={"target_user_id": u1})
        self.assertEqual(acc.status_code, 200)
        self.assertEqual(acc.json()["status"], "accepted")

        pty = self.client.post("/api/v1/social/party/create", headers=h1, json={"name": "Suryanagar Explorers"}).json()
        join = self.client.post("/api/v1/social/party/join", headers=h2, json={"party_id": pty["party_id"]})
        self.assertEqual(join.status_code, 200)
        members = self.client.get(f"/api/v1/social/party/{pty['party_id']}", headers=h1).json()["members"]
        self.assertEqual(len(members), 2)

        with self.client.websocket_connect(f"/api/v1/social/ws/chat?token={t1}") as ws:
            ws.send_text("Hello Suryanagar!")
            ok_msg = ws.receive_json()
            self.assertTrue(ok_msg["delivered"])
            ws.send_text("b o m b the station tomorrow")
            blk_msg = ws.receive_json()
            self.assertFalse(blk_msg["delivered"])

    def test_04_moderation_stages_appeals_emergency_and_unicode(self):
        _, _, ph = self._register_and_char("mod_stages_user")
        f_tok = self.client.post("/api/v1/auth/register", json={"username": "divyesh_bambhaniya", "password": "FounderPass!"}).json()["access_token"]
        fh = {"Authorization": f"Bearer {f_tok}"}

        # Gujarati & Devanagari safe educational context allowed
        gu_safe = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "ગુજરાતનો ઇતિહાસ અને સુરક્ષા અભ્યાસ"})
        self.assertTrue(gu_safe.json()["delivered"])
        hi_safe = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "इतिहास और परीक्षा की तैयारी"})
        self.assertTrue(hi_safe.json()["delivered"])

        # Stage 1 warning
        s1 = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "attackers are heroes"})
        self.assertEqual(s1.json()["warning_stage"], 1)

        # Stage 2 warning -> temp chat restriction
        s2 = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "humlo saru karyo"})
        self.assertEqual(s2.json()["warning_stage"], 2)
        ev_id = s2.json()["moderation_event_id"]

        # Restricted user cannot chat
        blocked_chat = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "hi"})
        self.assertEqual(blocked_chat.status_code, 403)

        # Appeal & Founder overturn
        self.client.post("/api/v1/moderation/appeal", headers=ph, json={"moderation_event_id": ev_id, "reason": "False positive test appeal"})
        rev = self.client.post("/api/v1/moderation/review-appeal", headers=fh, json={"moderation_event_id": ev_id, "appeal_decision": "approved_overturned"})
        self.assertEqual(rev.json()["appeal_status"], "approved_overturned")

        # Imminent emergency threat -> immediate protective suspension
        em = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "station par bomb mukishu tomorrow"})
        self.assertFalse(em.json()["delivered"])
        after_em = self.client.post("/api/v1/moderation/check-message", headers=ph, json={"channel": "public_chat", "message": "hello"})
        self.assertEqual(after_em.status_code, 403)

    def test_05_disposable_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bak_path = os.path.join(tmpdir, "disposable_backup.db")
            restored_path = os.path.join(tmpdir, "disposable_restored.db")
            manifest = create_sqlite_backup(_TMP_DB.name, bak_path)
            self.assertTrue(os.path.exists(bak_path))
            self.assertEqual(len(manifest["sha256"]), 64)
            self.assertTrue(restore_sqlite_backup(bak_path, restored_path))
            self.assertTrue(os.path.exists(restored_path))


if __name__ == "__main__":
    unittest.main()
