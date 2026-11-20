import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import BASE_DIR, DATABASE_URL

IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras


def _sqlite_path() -> str:
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.replace("sqlite:///", "", 1)
    return str(BASE_DIR / "02_BACKEND" / "lifeverse_local.db")


def _adapt_sql(sql: str) -> str:
    if IS_POSTGRES:
        return sql.replace("?", "%s")
    return sql


class DBWrapper:
    def __init__(self, conn: Any):
        self._conn = conn

    def execute(self, sql: str, params: tuple = ()) -> Any:
        cur = self._conn.cursor()
        cur.execute(_adapt_sql(sql), params)
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
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield DBWrapper(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        path = _sqlite_path()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield DBWrapper(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db() -> None:
    schema_file = (
        BASE_DIR / "03_DATABASE" / "schemas" / ("001_initial_postgresql.sql" if IS_POSTGRES else "002_sqlite_compatible.sql")
    )
    sql_script = schema_file.read_text(encoding="utf-8")
    with get_db() as db:
        if IS_POSTGRES:
            for stmt in [s.strip() for s in sql_script.split(";") if s.strip()]:
                db.execute(stmt)
        else:
            db._conn.executescript(sql_script)
