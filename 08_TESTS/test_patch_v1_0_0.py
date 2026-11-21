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
from app.security import compute_totp  # noqa: E402


class TestPatchV100(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(_TMP_DB.name):
            os.unlink(_TMP_DB.name)

    def test_01_production_security_headers_and_version(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["version"], "1.0.0")
        self.assertEqual(res.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(res.headers.get("x-frame-options"), "DENY")

    def test_02_totp_2fa_setup_verify_and_enforced_login(self):
        reg = self.client.post("/api/v1/auth/register", json={"username": "secure_founder_test", "password": "Password123"}).json()
        headers = {"Authorization": f"Bearer {reg['access_token']}"}

        setup = self.client.post("/api/v1/auth/2fa/setup", headers=headers)
        self.assertEqual(setup.status_code, 200)
        secret = setup.json()["totp_secret"]
        self.assertIn("otpauth://totp/LIFEVERSE2070:", setup.json()["otpauth_uri"])

        # Wrong code fails
        bad = self.client.post("/api/v1/auth/2fa/verify", headers=headers, json={"code": "000000"})
        self.assertEqual(bad.status_code, 400)

        # Valid RFC 6238 code enables 2FA
        valid_code = compute_totp(secret)
        ok = self.client.post("/api/v1/auth/2fa/verify", headers=headers, json={"code": valid_code})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.json()["enabled"])

        # Login without TOTP must be rejected
        no_totp = self.client.post("/api/v1/auth/login", json={"username": "secure_founder_test", "password": "Password123"})
        self.assertEqual(no_totp.status_code, 401)

        # Login with valid TOTP succeeds
        with_totp = self.client.post("/api/v1/auth/login", json={"username": "secure_founder_test", "password": "Password123", "totp_code": compute_totp(secret)})
        self.assertEqual(with_totp.status_code, 200)

    def test_03_password_reset_flow_and_single_use_token(self):
        self.client.post("/api/v1/auth/register", json={"username": "reset_user", "password": "OldPassword123"})
        req = self.client.post("/api/v1/auth/password-reset/request", json={"username": "reset_user"})
        self.assertEqual(req.status_code, 200)
        tok = req.json()["dev_reset_token"]

        conf = self.client.post("/api/v1/auth/password-reset/confirm", json={"username": "reset_user", "reset_token": tok, "new_password": "NewPassword456"})
        self.assertEqual(conf.status_code, 200)

        # Token cannot be reused
        reuse = self.client.post("/api/v1/auth/password-reset/confirm", json={"username": "reset_user", "reset_token": tok, "new_password": "AnotherPassword789"})
        self.assertEqual(reuse.status_code, 400)

        # Login succeeds with new password
        login = self.client.post("/api/v1/auth/login", json={"username": "reset_user", "password": "NewPassword456"})
        self.assertEqual(login.status_code, 200)


if __name__ == "__main__":
    unittest.main()
