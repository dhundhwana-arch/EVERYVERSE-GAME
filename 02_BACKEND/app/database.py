import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import BASE_DIR, validate_production_config


def _current_db_url() -> str:
    env = os.getenv("LIFEVERSE_ENV", "development").lower()
    url = os.getenv("DATABASE_URL", "")
    if env == "production":
        if not (url.startswith("postgresql://") or url.startswith("postgres://")):
            raise RuntimeError("PRODUCTION ERROR: Valid PostgreSQL DATABASE_URL is required; SQLite is disabled in production.")
        return url
    return url or f"sqlite:///{BASE_DIR / '02_BACKEND' / 'lifeverse_local.db'}"


def is_postgres_url(url: str) -> bool:
    return url.startswith("postgres://") or url.startswith("postgresql://")


def _sqlite_path(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return str(BASE_DIR / "02_BACKEND" / "lifeverse_local.db")


class DBWrapper:
    def __init__(self, conn: Any, postgres: bool):
        self._conn = conn
        self._postgres = postgres

    def execute(self, sql: str, params: tuple = ()) -> Any:
        cur = self._conn.cursor()
        adapted = sql.replace("?", "%s") if self._postgres else sql
        cur.execute(adapted, params)
        return cur

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        cur = self.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        if isinstance(row, sqlite3.Row):
            return dict(row)
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = self.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], sqlite3.Row):
            return [dict(r) for r in rows]
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


@contextmanager
def get_db() -> Iterator[DBWrapper]:
    url = _current_db_url()
    pg = is_postgres_url(url)
    if pg:
        import psycopg2
        conn = psycopg2.connect(url)
        try:
            yield DBWrapper(conn, postgres=True)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        path = _sqlite_path(url)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield DBWrapper(conn, postgres=False)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db() -> None:
    validate_production_config()
    url = _current_db_url()
    pg = is_postgres_url(url)
    schema_file = (
        BASE_DIR / "03_DATABASE" / "schemas" / ("001_initial_postgresql.sql" if pg else "002_sqlite_compatible.sql")
    )
    sql_script = schema_file.read_text(encoding="utf-8")
    with get_db() as db:
        if pg:
            for stmt in [s.strip() for s in sql_script.split(";") if s.strip()]:
                db.execute(stmt)
        else:
            db._conn.executescript(sql_script)
