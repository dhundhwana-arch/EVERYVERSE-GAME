import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV = os.getenv("LIFEVERSE_ENV", "development").lower()
IS_PRODUCTION = ENV == "production"

_DEV_SECRET = "dev-only-lifeverse-2070-secret-change-in-prod"
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET)
DATABASE_URL = os.getenv("DATABASE_URL", "" if IS_PRODUCTION else f"sqlite:///{BASE_DIR / '02_BACKEND' / 'lifeverse_local.db'}")
OFFICIAL_BRANDING = "CREATED BY DIVYESH BAMBHANIYA"

MODERATION_CONFIG_JSON = os.getenv("MODERATION_CONFIG_JSON", "")
MODERATION_CONFIG_PATH = os.getenv(
    "MODERATION_CONFIG_PATH",
    "/etc/secrets/private_moderation_config.json" if IS_PRODUCTION else str(BASE_DIR / "06_SECURITY" / "private_moderation_config.json"),
)

# Strict CORS origins (never wildcard '*' with allow_credentials=True in production)
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:8000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip() and o.strip() != "*"]

# Email delivery settings for password reset (fail-safe if unconfigured)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


def validate_production_config() -> None:
    """Fail fast in production if critical security or database settings are unsafe."""
    if not IS_PRODUCTION:
        return
    if not DATABASE_URL or not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")):
        raise RuntimeError("PRODUCTION ERROR: Valid PostgreSQL DATABASE_URL is mandatory. SQLite fallback is forbidden.")
    if not SECRET_KEY or SECRET_KEY == _DEV_SECRET or len(SECRET_KEY) < 32:
        raise RuntimeError("PRODUCTION ERROR: SECRET_KEY must be a strong random secret (>= 32 chars).")
    if not ALLOWED_ORIGINS:
        raise RuntimeError("PRODUCTION ERROR: Explicit ALLOWED_ORIGINS must be configured (wildcard '*' is forbidden).")
