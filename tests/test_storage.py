import sqlite3
import tempfile
from pathlib import Path

from src.storage import get_connection, init_db, upsert_skills, list_new_skills


def test_dedup_insert_and_detect_new(tmp_path):
    db_path = tmp_path / "skills.db"
    conn = get_connection(str(db_path))
    init_db(conn)

    skills = [
        {
            "id_key": "key1",
            "name": "SkillA",
            "url": "https://skills.sh/a",
            "category": "a",
            "description": "",
            "discovered_at": "2026-03-15T00:00:00Z",
            "raw": "{}",
        },
        {
            "id_key": "key2",
            "name": "SkillB",
            "url": "https://skills.sh/b",
            "category": "b",
            "description": "",
            "discovered_at": "2026-03-15T00:00:00Z",
            "raw": "{}",
        },
    ]

    new1 = list_new_skills(conn, skills)
    assert len(new1) == 2

    ins, skip, total = upsert_skills(conn, new1)
    assert ins == 2 and skip == 0 and total == 2

    dup = list_new_skills(conn, skills)
    assert len(dup) == 0

    skills.append(
        {
            "id_key": "key3",
            "name": "SkillC",
            "url": "https://skills.sh/c",
            "category": "c",
            "description": "",
            "discovered_at": "2026-03-15T00:00:00Z",
            "raw": "{}",
        }
    )
    latest = list_new_skills(conn, skills)
    assert len(latest) == 1
    assert latest[0]["id_key"] == "key3"
