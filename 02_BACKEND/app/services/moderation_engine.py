import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, IS_PRODUCTION

_CHAR_MAP = str.maketrans({
    "@": "a", "4": "a", "3": "e", "1": "i", "!": "i", "0": "o", "$": "s", "5": "s", "7": "t",
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0445": "x",
})


def load_moderation_config() -> dict[str, Any]:
    """
    Load private moderation rules securely from:
      1. MODERATION_CONFIG_JSON environment variable (recommended for Render / cloud secrets), OR
      2. MODERATION_CONFIG_PATH secret file (e.g. /etc/secrets/private_moderation_config.json).
    Fails closed if unconfigured in production.
    """
    raw_json = os.getenv("MODERATION_CONFIG_JSON", "").strip()
    if raw_json:
        return json.loads(raw_json)

    cfg_path = os.getenv(
        "MODERATION_CONFIG_PATH",
        "/etc/secrets/private_moderation_config.json" if IS_PRODUCTION else str(BASE_DIR / "06_SECURITY" / "private_moderation_config.json"),
    )
    path = Path(cfg_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    if IS_PRODUCTION:
        raise RuntimeError("PRODUCTION ERROR: Private moderation configuration not found in MODERATION_CONFIG_JSON or MODERATION_CONFIG_PATH.")
    # Safe minimal fallback for non-production environments if local private file was untracked
    example = BASE_DIR / "06_SECURITY" / "moderation_config.example.json"
    if example.exists():
        return json.loads(example.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Moderation config not found at {cfg_path}")


def normalize_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw).lower()
    text = text.translate(_CHAR_MAP)
    text = re.sub(r"\b([a-z])\s+(?=[a-z]\b)", r"\1", text)
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    text = re.sub(r"[^\w\s\u0A80-\u0AFF\u0900-\u097F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def evaluate_message(raw_text: str, channel: str = "chat", media_type: str = "text") -> dict[str, Any]:
    cfg = load_moderation_config()
    normalized = normalize_text(raw_text)
    collapsed = normalized.replace(" ", "")

    matched_category = None
    matched_label = "none"
    severity = "none"

    for cat_id, cat_data in cfg["categories"].items():
        for sig in cat_data["signals"]:
            sig_norm = normalize_text(sig)
            if sig_norm and (sig_norm in normalized or sig_norm.replace(" ", "") in collapsed):
                matched_category = cat_id
                matched_label = cat_data["label"]
                severity = cat_data["base_severity"]
                break
        if matched_category:
            break

    if not matched_category:
        return {
            "allowed": True,
            "decision": "allow",
            "category": "NONE",
            "category_label": "Safe",
            "severity": "none",
            "review_status": "auto_resolved",
            "requires_human_review": False,
            "imminent_emergency": False,
            "explanation": "Message passed safety checks.",
        }

    benign_hits = sum(1 for m in cfg["benign_context_markers"] if normalize_text(m) in normalized)
    intent_hits = sum(1 for m in cfg["harmful_intent_markers"] if normalize_text(m) in normalized)

    if benign_hits >= 1 and intent_hits == 0 and severity != "critical":
        return {
            "allowed": True,
            "decision": "allow_educational_context",
            "category": matched_category,
            "category_label": matched_label,
            "severity": "low",
            "review_status": "auto_resolved",
            "requires_human_review": False,
            "imminent_emergency": False,
            "explanation": "Permitted under educational, historical, news, or fictional context.",
        }

    if benign_hits >= 1 and severity == "critical" and intent_hits == 0:
        return {
            "allowed": False,
            "decision": "hold_for_review",
            "category": matched_category,
            "category_label": matched_label,
            "severity": "medium",
            "review_status": "pending_review",
            "requires_human_review": True,
            "imminent_emergency": False,
            "explanation": "Message held for human moderator review due to mixed sensitive and educational context.",
        }

    imminent = severity == "critical" and intent_hits >= 1
    return {
        "allowed": False,
        "decision": "block",
        "category": matched_category,
        "category_label": matched_label,
        "severity": severity,
        "review_status": "escalated" if imminent else "auto_blocked",
        "requires_human_review": imminent,
        "imminent_emergency": imminent,
        "explanation": f"Blocked under rule: {matched_label}.",
    }
