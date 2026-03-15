"""SQLite persistence for discovered skills with deduplication."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Sequence, Tuple

from src import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  id_key TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  category TEXT,
  description TEXT,
  rank INTEGER,
  install_count INTEGER,
  discovered_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  raw TEXT
);
"""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = config.get_db_path() if db_path is None else db_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(skills)").fetchall()}

    if "rank" not in columns:
        conn.execute("ALTER TABLE skills ADD COLUMN rank INTEGER")
    if "install_count" not in columns:
        conn.execute("ALTER TABLE skills ADD COLUMN install_count INTEGER")


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(SCHEMA)
    _ensure_columns(conn)
    conn.commit()


def _to_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_skills(conn: sqlite3.Connection, skills: Sequence[Dict[str, str]]) -> Tuple[int, int, int]:
    """Insert skills and return inserted, skipped, total."""
    inserted = 0
    skipped = 0
    init_db(conn)
    with conn:
        for skill in skills:
            payload = {
                "id_key": skill["id_key"],
                "name": skill.get("name", "") or "",
                "url": skill.get("url", "") or "",
                "category": skill.get("category", ""),
                "description": skill.get("description", ""),
                "rank": skill.get("rank"),
                "install_count": skill.get("install_count"),
                "discovered_at": skill.get("discovered_at", _to_iso_now()),
                "created_at": _to_iso_now(),
                "raw": skill.get("raw", ""),
            }
            try:
                conn.execute(
                    """
                    INSERT INTO skills (id_key, name, url, category, description, rank, install_count, discovered_at, created_at, raw)
                    VALUES (:id_key, :name, :url, :category, :description, :rank, :install_count, :discovered_at, :created_at, :raw)
                    """,
                    payload,
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return inserted, skipped, len(skills)


def list_new_skills(conn: sqlite3.Connection, current_run_skills: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    init_db(conn)
    if not current_run_skills:
        return []

    id_keys = [s.get("id_key") for s in current_run_skills if s.get("id_key")]
    if not id_keys:
        return []

    placeholders = ",".join("?" for _ in id_keys)
    existing_rows = conn.execute(
        f"SELECT id_key FROM skills WHERE id_key IN ({placeholders})",
        id_keys,
    ).fetchall()
    existing = {row["id_key"] for row in existing_rows}
    return [s for s in current_run_skills if s.get("id_key") not in existing]


def ensure_schema_and_get_ids(conn: sqlite3.Connection, skills: Sequence[Dict[str, str]]) -> List[str]:
    init_db(conn)
    if not skills:
        return []
    init_ids = [s.get("id_key") for s in skills]
    placeholders = ",".join("?" for _ in init_ids)
    existing_rows = conn.execute(
        f"SELECT id_key FROM skills WHERE id_key IN ({placeholders})",
        init_ids,
    ).fetchall()
    return [row["id_key"] for row in existing_rows]


def list_skills_ordered(conn: sqlite3.Connection, limit: int = 20):
    init_db(conn)
    return conn.execute(
        "SELECT id,name,url,category,description,rank,install_count,discovered_at,created_at FROM skills ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
