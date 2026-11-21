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
from app.bootstrap_founder import provision_founder  # noqa: E402
from app.database import _current_db_url, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402
from app.security import compute_totp, create_access_token  # noqa: E402


class TestSecurityFixesV101(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        auth_router._EMAIL_DELIVERY_HOOK = None
        if os.path.exists(_TMP_DB.name):
            os.unlink(_TMP_DB.name)

    def test_01_public_registration_never_grants_founder_role(self):
        # Attempting to register with the Founder's name MUST assign 'player' and deny /admin/overview
        res = self.client.post("/api/v1/auth/register", json={"username": "divyesh_bambhaniya", "password": "Password123"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "player")

        headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
        admin_res = self.client.get("/api/v1/admin/overview", headers=headers)
        self.assertEqual(admin_res.status_code, 403)

    def test_02_password_reset_fails_safely_503_when_smtp_unconfigured(self):
        auth_router._EMAIL_DELIVERY_HOOK = None
        self.client.post("/api/v1/auth/register", json={"username": "no_smtp_user", "email": "nosmtp@example.com", "password": "Password123"})
        res = self.client.post("/api/v1/auth/password-reset/request", json={"username": "no_smtp_user"})
        self.assertEqual(res.status_code, 503)
        self.assertNotIn("dev_reset_token", res.text)

    def test_03_mandatory_founder_mfa_and_anti_bypass(self):
        f = provision_founder("preprovisioned_founder", "FounderStrong99", email="f@lifeverse2070.example")

        # 1. Login without TOTP fails (401)
        no_code = self.client.post("/api/v1/auth/login", json={"username": "preprovisioned_founder", "password": "FounderStrong99"})
        self.assertEqual(no_code.status_code, 401)

        # 2. Forged/unverified MFA token is rejected on Founder route (403)
        unverified_tok = create_access_token(f["user_id"], f["username"], "founder", mfa_verified=False)
        bypass_try = self.client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {unverified_tok}"})
        self.assertEqual(bypass_try.status_code, 403)

        # 3. Valid TOTP login succeeds and grants Founder overview
        ok_login = self.client.post(
            "/api/v1/auth/login",
            json={"username": "preprovisioned_founder", "password": "FounderStrong99", "totp_code": compute_totp(f["totp_secret"])},
        )
        self.assertEqual(ok_login.status_code, 200)
        fh = {"Authorization": f"Bearer {ok_login.json()['access_token']}"}
        self.assertEqual(self.client.get("/api/v1/admin/overview", headers=fh).status_code, 200)

        # 4. Cannot overwrite enabled 2FA without current TOTP code
        overwrite_try = self.client.post("/api/v1/auth/2fa/setup", headers=fh, json={})
        self.assertEqual(overwrite_try.status_code, 403)

        # 5. Founder password reset via public endpoint is blocked
        reset_try = self.client.post("/api/v1/auth/password-reset/request", json={"username": "preprovisioned_founder"})
        self.assertEqual(reset_try.status_code, 403)

    def test_04_production_rejects_sqlite_fallback(self):
        old_env = os.environ.get("LIFEVERSE_ENV")
        old_url = os.environ.get("DATABASE_URL")
        try:
            os.environ["LIFEVERSE_ENV"] = "production"
            os.environ["DATABASE_URL"] = "sqlite:///ephemeral.db"
            with self.assertRaises(RuntimeError):
                _current_db_url()
        finally:
            if old_env is None:
                os.environ.pop("LIFEVERSE_ENV", None)
            else:
                os.environ["LIFEVERSE_ENV"] = old_env
            if old_url is not None:
                os.environ["DATABASE_URL"] = old_url

    def test_05_weak_password_rejected_and_render_yaml_valid(self):
        weak = self.client.post("/api/v1/auth/register", json={"username": "weak_pw_user", "password": "onlyletters"})
        self.assertEqual(weak.status_code, 400)

        render_text = (ROOT_DIR / "render.yaml").read_text(encoding="utf-8")
        self.assertIn("rootDir: .", render_text)
        self.assertIn("buildCommand: pip install -r 02_BACKEND/requirements.txt", render_text)
        self.assertIn("PYTHONPATH=02_BACKEND uvicorn app.main:app", render_text)
        self.assertIn("/etc/secrets/private_moderation_config.json", render_text)


if __name__ == "__main__":
    unittest.main()
