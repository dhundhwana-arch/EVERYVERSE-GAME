import hashlib
import json
import sqlite3
from pathlib import Path


def create_sqlite_backup(db_path: str, backup_file: str) -> dict:
    """Create a consistent SQLite backup snapshot and SHA-256 checksum manifest."""
    src = sqlite3.connect(db_path)
    Path(backup_file).parent.mkdir(parents=True, exist_ok=True)
    dst = sqlite3.connect(backup_file)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    digest = hashlib.sha256(Path(backup_file).read_bytes()).hexdigest()
    manifest_path = f"{backup_file}.sha256.json"
    manifest = {"backup_file": str(backup_file), "sha256": digest}
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def restore_sqlite_backup(backup_file: str, target_db_path: str) -> bool:
    """Verify SHA-256 checksum and restore backup onto a target database."""
    manifest = json.loads(Path(f"{backup_file}.sha256.json").read_text(encoding="utf-8"))
    actual_digest = hashlib.sha256(Path(backup_file).read_bytes()).hexdigest()
    if actual_digest != manifest["sha256"]:
        raise ValueError("Backup integrity check failed: SHA-256 mismatch")

    src = sqlite3.connect(backup_file)
    Path(target_db_path).parent.mkdir(parents=True, exist_ok=True)
    dst = sqlite3.connect(target_db_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return True
