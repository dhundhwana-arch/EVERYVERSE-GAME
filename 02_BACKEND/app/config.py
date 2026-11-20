import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV = os.getenv("LIFEVERSE_ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-lifeverse-2070-secret-change-in-prod")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / '02_BACKEND' / 'lifeverse_local.db'}")
FOUNDER_USERNAME = os.getenv("FOUNDER_USERNAME", "divyesh_bambhaniya")
OFFICIAL_BRANDING = "CREATED BY DIVYESH BAMBHANIYA"

MODERATION_CONFIG_PATH = os.getenv(
    "MODERATION_CONFIG_PATH",
    str(BASE_DIR / "06_SECURITY" / "private_moderation_config.json"),
)
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
