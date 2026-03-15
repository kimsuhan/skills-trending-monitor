import sqlite3
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
            "rank": 1,
            "install_count": 12,
        },
        {
            "id_key": "key2",
            "name": "SkillB",
            "url": "https://skills.sh/b",
            "category": "b",
            "description": "",
            "discovered_at": "2026-03-15T00:00:00Z",
            "raw": "{}",
            "rank": 2,
            "install_count": 34,
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
            "rank": None,
            "install_count": None,
        }
    )
    latest = list_new_skills(conn, skills)
    assert len(latest) == 1
    assert latest[0]["id_key"] == "key3"


def test_init_db_migrates_old_schema(tmp_path):
    db_path = tmp_path / "skills_legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skills (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          id_key TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL,
          url TEXT NOT NULL,
          category TEXT,
          description TEXT,
          discovered_at TEXT NOT NULL,
          created_at TEXT NOT NULL,
          raw TEXT
        )
        """
    )
    conn.commit()

    init_db(conn)
    col_names = {row[1] for row in conn.execute('PRAGMA table_info(skills)').fetchall()}
    assert 'rank' in col_names
    assert 'install_count' in col_names
